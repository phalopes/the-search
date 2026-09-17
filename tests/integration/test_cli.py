import httpx
import pytest
import respx
from typer.testing import CliRunner

from surfscout.adapters.weather import open_meteo
from surfscout.app.cli import app

pytestmark = pytest.mark.integration

runner = CliRunner()

MARINE_BODY = {
    "hourly": {
        "time": ["2026-09-10T07:00"],
        "swell_wave_height_gwam": [1.2],
        "swell_wave_direction_gwam": [110],
        "swell_wave_period_gwam": [10],
        "sea_level_height_msl_marine_best_match": [0.5],
    }
}

WIND_BODY = {
    "hourly": {
        "time": ["2026-09-10T07:00"],
        "wind_speed_10m": [5.0],
        "wind_direction_10m": [290],
    }
}


@respx.mock
def test_recommend_roda_e_lista_os_picos_ranqueados() -> None:
    respx.get(open_meteo.MARINE_URL).mock(return_value=httpx.Response(200, json=MARINE_BODY))
    respx.get(open_meteo.FORECAST_URL).mock(return_value=httpx.Response(200, json=WIND_BODY))

    resultado = runner.invoke(app, ["--when", "2026-09-10T07:00", "--nivel", "intermediario"])

    assert resultado.exit_code == 0, resultado.output
    assert "Recomendação para 2026-09-10T07:00" in resultado.output
    assert "Mole" in resultado.output
    assert "Joaquina" in resultado.output
