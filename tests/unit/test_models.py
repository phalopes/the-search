import pytest
from pydantic import ValidationError

from surfscout.domain.models import SpotProfile

pytestmark = pytest.mark.unit


def _spot_dict(**overrides: object) -> dict:
    base: dict = {
        "id": "teste",
        "nome": "Pico Teste",
        "regiao": "Florianópolis, SC",
        "coordenadas": {"lat": -27.6, "lon": -48.4},
        "fundo": "areia",
        "nivel": "intermediario",
        "deslocamento_min": 20,
        "swell_ideal": {"direcao_min_graus": 90, "direcao_max_graus": 140},
        "vento_ideal": {"direcao_offshore_min_graus": 270, "direcao_offshore_max_graus": 320},
        "mare_ideal": {
            "fase_preferida": "sem_preferencia_clara",
            "altura_min_m": 0.2,
            "altura_max_m": 0.8,
        },
        "tamanho_ideal": {"altura_min_m": 0.8, "altura_max_m": 1.8},
    }
    base.update(overrides)
    return base


def test_spot_profile_valido_eh_aceito() -> None:
    spot = SpotProfile.model_validate(_spot_dict())
    assert spot.id == "teste"
    assert spot.swell_ideal.periodo_min_s is None


def test_nivel_invalido_eh_rejeitado() -> None:
    with pytest.raises(ValidationError):
        SpotProfile.model_validate(_spot_dict(nivel="lendario"))


def test_fase_preferida_invalida_eh_rejeitada() -> None:
    dados = _spot_dict()
    dados["mare_ideal"] = {**dados["mare_ideal"], "fase_preferida": "cheia"}
    with pytest.raises(ValidationError):
        SpotProfile.model_validate(dados)


def test_direcao_fora_de_0_360_eh_rejeitada() -> None:
    dados = _spot_dict()
    dados["swell_ideal"] = {**dados["swell_ideal"], "direcao_min_graus": 400}
    with pytest.raises(ValidationError):
        SpotProfile.model_validate(dados)
