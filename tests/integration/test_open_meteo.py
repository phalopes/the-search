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
        "swell_wave_height_gwam": [1.0, 1.2, 1.3],
        "swell_wave_direction_gwam": [100, 110, 115],
        "swell_wave_period_gwam": [9, 10, 10],
        "sea_level_height_msl_marine_best_match": [0.3, 0.5, 0.6],
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

    assert marine_route.calls.last.request.url.params["models"] == open_meteo.MARINE_MODELS


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


@respx.mock
def test_fetch_readings_usa_gwam_pro_swell_e_best_match_pra_mare() -> None:
    """Regressão: gwam tem período/altura mais precisos (ver docs/validacao/2026-09-17/),
    mas não retorna sea_level_height_msl — a maré tem que continuar vindo do best_match,
    nunca ser lida (ou zerada) a partir do campo do gwam."""
    corpo = {
        "hourly": {
            "time": ["2026-09-17T07:00"],
            "swell_wave_height_marine_best_match": [0.6],
            "swell_wave_period_marine_best_match": [6.5],
            "swell_wave_direction_marine_best_match": [162],
            "sea_level_height_msl_marine_best_match": [0.23],
            "swell_wave_height_gwam": [1.04],
            "swell_wave_period_gwam": [7.85],
            "swell_wave_direction_gwam": [160],
            "sea_level_height_msl_gwam": [None],
        }
    }
    respx.get(open_meteo.MARINE_URL).mock(return_value=httpx.Response(200, json=corpo))
    respx.get(open_meteo.FORECAST_URL).mock(return_value=httpx.Response(200, json=WIND_BODY))

    swell, _vento, mare = open_meteo.fetch_readings(COORDENADAS, at=dt.datetime(2026, 9, 17, 7, 0))

    assert swell.altura_m == 1.04
    assert swell.periodo_s == 7.85
    assert mare.altura_m == 0.23
