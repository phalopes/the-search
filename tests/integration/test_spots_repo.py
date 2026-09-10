from pathlib import Path

import pytest

from surfscout.adapters.storage.spots_repo import load_spots

pytestmark = pytest.mark.integration

SPOTS_PATH = Path(__file__).resolve().parents[2] / "src" / "surfscout" / "spots.yaml"


def test_carrega_os_5_picos_reais_do_projeto() -> None:
    spots = load_spots(SPOTS_PATH)

    assert {spot.id for spot in spots} == {
        "mole",
        "campeche",
        "matadeiro",
        "joaquina",
        "barra-da-lagoa",
    }


def test_todos_os_picos_tem_coordenadas_em_florianopolis() -> None:
    spots = load_spots(SPOTS_PATH)

    for spot in spots:
        assert -28.5 < spot.coordenadas.lat < -27.0
        assert -49.0 < spot.coordenadas.lon < -48.0
