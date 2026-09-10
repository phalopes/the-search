import datetime as dt

import httpx
import pytest
import respx

from surfscout.adapters.weather import open_meteo
from surfscout.domain.models import Coordenadas, TidePhase

pytestmark = pytest.mark.integration

COORDENADAS = Coordenadas(lat=-27.6, lon=-48.4)

MARINE_BODY = {
    "hourly": {
        "time": ["2026-09-10T06:00", "2026-09-10T07:00", "2026-09-10T08:00"],
        "swell_wave_height": [1.0, 1.2, 1.3],
        "swell_wave_direction": [100, 110, 115],
        "swell_wave_period": [9, 10, 10],
        "sea_level_height_msl": [0.3, 0.5, 0.6],
    }
}

WIND_BODY = {
    "hourly": {
        "time": ["2026-09-10T06:00", "2026-09-10T07:00", "2026-09-10T08:00"],
        "wind_speed_10m": [4.0, 5.0, 6.0],
        "wind_direction_10m": [280, 290, 295],
    }
}


@respx.mock
def test_fetch_readings_pega_a_hora_mais_proxima_e_calcula_fase_da_mare() -> None:
    respx.get(open_meteo.MARINE_URL).mock(return_value=httpx.Response(200, json=MARINE_BODY))
    respx.get(open_meteo.FORECAST_URL).mock(return_value=httpx.Response(200, json=WIND_BODY))

    swell, vento, mare = open_meteo.fetch_readings(COORDENADAS, at=dt.datetime(2026, 9, 10, 7, 5))

    assert swell.altura_m == 1.2
    assert swell.direcao_graus == 110
    assert vento.velocidade_ms == 5.0
    assert mare.altura_m == 0.5
    assert mare.fase == TidePhase.ENCHENTE  # 0.5 > 0.3 (hora anterior)


@respx.mock
def test_fetch_readings_fixa_o_parametro_models_explicitamente() -> None:
    marine_route = respx.get(open_meteo.MARINE_URL).mock(
        return_value=httpx.Response(200, json=MARINE_BODY)
    )
    respx.get(open_meteo.FORECAST_URL).mock(return_value=httpx.Response(200, json=WIND_BODY))

    open_meteo.fetch_readings(COORDENADAS, at=dt.datetime(2026, 9, 10, 7, 0))

    assert marine_route.calls.last.request.url.params["models"] == open_meteo.MODEL


@respx.mock
def test_erro_5xx_transitorio_eh_reprocessado_e_se_recupera() -> None:
    route = respx.get(open_meteo.MARINE_URL).mock(
        side_effect=[httpx.Response(500), httpx.Response(200, json=MARINE_BODY)]
    )
    respx.get(open_meteo.FORECAST_URL).mock(return_value=httpx.Response(200, json=WIND_BODY))

    open_meteo.fetch_readings(COORDENADAS, at=dt.datetime(2026, 9, 10, 7, 0))

    assert route.call_count == 2


@respx.mock
def test_erro_4xx_nao_eh_reprocessado() -> None:
    route = respx.get(open_meteo.MARINE_URL).mock(return_value=httpx.Response(400))
    respx.get(open_meteo.FORECAST_URL).mock(return_value=httpx.Response(200, json=WIND_BODY))

    with pytest.raises(httpx.HTTPStatusError):
        open_meteo.fetch_readings(COORDENADAS, at=dt.datetime(2026, 9, 10, 7, 0))

    assert route.call_count == 1


def test_tide_phase_sem_leitura_anterior_eh_indeterminada() -> None:
    assert open_meteo._tide_phase([None, 0.5], 0) == TidePhase.INDETERMINADA
    assert open_meteo._tide_phase([0.5], 0) == TidePhase.INDETERMINADA


def test_tide_phase_altura_igual_eh_indeterminada() -> None:
    assert open_meteo._tide_phase([0.5, 0.5], 1) == TidePhase.INDETERMINADA
