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

    resultado = runner.invoke(
        app, ["recommend", "--when", "2026-09-10T07:00", "--nivel", "intermediario"]
    )

    assert resultado.exit_code == 0, resultado.output
    assert "Recomendação para 2026-09-10T07:00" in resultado.output
    assert "Mole" in resultado.output
    assert "Joaquina" in resultado.output


def test_log_e_historico_fazem_o_ciclo_completo(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "historico.db"

    resultado_log = runner.invoke(
        app,
        [
            "log",
            "--data",
            "2026-09-22",
            "--pico",
            "matadeiro",
            "--nota",
            "4",
            "--obs",
            "Vento sul bateu certinho",
            "--pico-recomendado",
            "matadeiro",
            "--score-recomendado",
            "90.2",
            "--db-path",
            str(db_path),
        ],
    )
    assert resultado_log.exit_code == 0, resultado_log.output
    assert "salvo em" in resultado_log.output

    resultado_historico = runner.invoke(app, ["historico", "--db-path", str(db_path)])
    assert resultado_historico.exit_code == 0, resultado_historico.output
    assert "matadeiro" in resultado_historico.output
    assert "nota 4/5" in resultado_historico.output
    assert "Vento sul bateu certinho" in resultado_historico.output


def test_log_rejeita_pico_inexistente(tmp_path) -> None:  # type: ignore[no-untyped-def]
    resultado = runner.invoke(
        app,
        [
            "log",
            "--data",
            "2026-09-22",
            "--pico",
            "pico-que-nao-existe",
            "--db-path",
            str(tmp_path / "historico.db"),
        ],
    )

    assert resultado.exit_code == 1
    assert "não encontrado" in resultado.output


def test_historico_sem_registros_avisa_vazio(tmp_path) -> None:  # type: ignore[no-untyped-def]
    resultado = runner.invoke(app, ["historico", "--db-path", str(tmp_path / "historico.db")])

    assert resultado.exit_code == 0
    assert "Nenhum registro encontrado" in resultado.output
