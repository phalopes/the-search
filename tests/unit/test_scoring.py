from datetime import datetime

import pytest

from surfscout.domain.models import (
    Coordenadas,
    FasePreferida,
    Fundo,
    MareIdeal,
    Nivel,
    NivelUsuario,
    SpotProfile,
    SwellIdeal,
    SwellReading,
    TamanhoIdeal,
    TidePhase,
    TideReading,
    VentoIdeal,
    WindReading,
)
from surfscout.domain.scoring import (
    _direction_match,
    _level_match,
    _period_match,
    _range_match,
    _speed_cap_match,
    _tide_phase_match,
    score_spot,
)

pytestmark = pytest.mark.unit


def _spot(**overrides: object) -> SpotProfile:
    base = {
        "id": "teste",
        "nome": "Pico Teste",
        "regiao": "Florianópolis, SC",
        "coordenadas": Coordenadas(lat=-27.6, lon=-48.4),
        "fundo": Fundo.AREIA,
        "nivel": Nivel.INTERMEDIARIO,
        "deslocamento_min": 20,
        "swell_ideal": SwellIdeal(direcao_min_graus=90, direcao_max_graus=140, periodo_min_s=8),
        "vento_ideal": VentoIdeal(direcao_offshore_min_graus=270, direcao_offshore_max_graus=320),
        "mare_ideal": MareIdeal(
            fase_preferida=FasePreferida.SEM_PREFERENCIA_CLARA, altura_min_m=0.2, altura_max_m=0.8
        ),
        "tamanho_ideal": TamanhoIdeal(altura_min_m=0.8, altura_max_m=1.8),
    }
    base.update(overrides)
    return SpotProfile.model_validate(base)


class TestDirectionMatch:
    def test_dentro_do_range_eh_match_perfeito(self) -> None:
        assert _direction_match(100, 90, 140) == 1.0

    def test_fora_do_range_alem_da_tolerancia_eh_zero(self) -> None:
        assert _direction_match(0, 90, 140) == 0.0

    @pytest.mark.parametrize("direcao,esperado", [(80, 0.5), (150, 0.5), (70, 0.0), (160, 0.0)])
    def test_decaimento_linear_fora_do_range(self, direcao: float, esperado: float) -> None:
        assert _direction_match(direcao, 90, 140) == pytest.approx(esperado, abs=1e-6)

    def test_range_que_cruza_o_zero(self) -> None:
        # range 350-30 (NNW a NNE passando pelo N)
        assert _direction_match(0, 350, 30) == 1.0
        assert _direction_match(340, 350, 30) == pytest.approx(0.5, abs=1e-6)
        assert _direction_match(180, 350, 30) == 0.0


class TestPeriodMatch:
    def test_dentro_do_minimo_eh_match_perfeito(self) -> None:
        assert _period_match(10, minimo=8, maximo=None) == 1.0

    def test_abaixo_do_minimo_decai(self) -> None:
        assert _period_match(6.5, minimo=8, maximo=None) == pytest.approx(0.5, abs=1e-6)

    def test_muito_abaixo_do_minimo_eh_zero(self) -> None:
        assert _period_match(3, minimo=8, maximo=None) == 0.0

    def test_sem_restricao_eh_sempre_match(self) -> None:
        assert _period_match(1, minimo=None, maximo=None) == 1.0

    def test_acima_do_maximo_decai(self) -> None:
        assert _period_match(16, minimo=None, maximo=14) == pytest.approx(1 - 2 / 3, abs=1e-6)


class TestRangeMatch:
    def test_dentro_do_range(self) -> None:
        assert _range_match(0.5, 0.2, 0.8, tolerancia=0.3) == 1.0

    def test_abaixo_decai_pela_tolerancia(self) -> None:
        assert _range_match(0.0, 0.2, 0.8, tolerancia=0.4) == pytest.approx(0.5, abs=1e-6)

    def test_acima_decai_pela_tolerancia(self) -> None:
        assert _range_match(1.2, 0.2, 0.8, tolerancia=0.4) == pytest.approx(0.0, abs=1e-6)


class TestSpeedCapMatch:
    def test_sem_teto_eh_sempre_match(self) -> None:
        assert _speed_cap_match(20, maximo=None) == 1.0

    def test_abaixo_do_teto_eh_match(self) -> None:
        assert _speed_cap_match(5, maximo=10) == 1.0

    def test_acima_do_teto_decai(self) -> None:
        assert _speed_cap_match(12, maximo=10) == pytest.approx(0.5, abs=1e-6)


class TestTidePhaseMatch:
    def test_sem_preferencia_clara_eh_sempre_match(self) -> None:
        mare = MareIdeal(
            fase_preferida=FasePreferida.SEM_PREFERENCIA_CLARA, altura_min_m=0.0, altura_max_m=1.0
        )
        assert _tide_phase_match(TidePhase.VAZANTE, 0.9, mare) == 1.0

    def test_fase_indeterminada_recebe_penalidade_leve(self) -> None:
        mare = MareIdeal(fase_preferida=FasePreferida.ENCHENTE, altura_min_m=0.0, altura_max_m=1.0)
        assert _tide_phase_match(TidePhase.INDETERMINADA, 0.5, mare) == 0.7

    def test_enchente_preferida_e_enchente_atual_eh_match(self) -> None:
        mare = MareIdeal(fase_preferida=FasePreferida.ENCHENTE, altura_min_m=0.0, altura_max_m=1.0)
        assert _tide_phase_match(TidePhase.ENCHENTE, 0.5, mare) == 1.0

    def test_enchente_preferida_e_vazante_atual_penaliza(self) -> None:
        mare = MareIdeal(fase_preferida=FasePreferida.ENCHENTE, altura_min_m=0.0, altura_max_m=1.0)
        assert _tide_phase_match(TidePhase.VAZANTE, 0.5, mare) == 0.3

    def test_vazante_preferida_e_vazante_atual_eh_match(self) -> None:
        mare = MareIdeal(fase_preferida=FasePreferida.VAZANTE, altura_min_m=0.0, altura_max_m=1.0)
        assert _tide_phase_match(TidePhase.VAZANTE, 0.5, mare) == 1.0

    def test_vazante_preferida_e_enchente_atual_penaliza(self) -> None:
        mare = MareIdeal(fase_preferida=FasePreferida.VAZANTE, altura_min_m=0.0, altura_max_m=1.0)
        assert _tide_phase_match(TidePhase.ENCHENTE, 0.5, mare) == 0.3

    def test_preamar_preferida_e_altura_no_teto_eh_match(self) -> None:
        mare = MareIdeal(fase_preferida=FasePreferida.PREAMAR, altura_min_m=0.0, altura_max_m=1.0)
        assert _tide_phase_match(TidePhase.ENCHENTE, 0.9, mare) == 1.0

    def test_preamar_preferida_e_altura_no_fundo_penaliza(self) -> None:
        mare = MareIdeal(fase_preferida=FasePreferida.PREAMAR, altura_min_m=0.0, altura_max_m=1.0)
        assert _tide_phase_match(TidePhase.VAZANTE, 0.1, mare) == 0.3

    def test_baixa_mar_preferida_e_altura_no_fundo_eh_match(self) -> None:
        mare = MareIdeal(fase_preferida=FasePreferida.BAIXA_MAR, altura_min_m=0.0, altura_max_m=1.0)
        assert _tide_phase_match(TidePhase.VAZANTE, 0.1, mare) == 1.0

    def test_baixa_mar_preferida_e_altura_no_teto_penaliza(self) -> None:
        mare = MareIdeal(fase_preferida=FasePreferida.BAIXA_MAR, altura_min_m=0.0, altura_max_m=1.0)
        assert _tide_phase_match(TidePhase.ENCHENTE, 0.9, mare) == 0.3

    def test_enchente_ate_inicio_vazante_aceita_enchente(self) -> None:
        mare = MareIdeal(
            fase_preferida=FasePreferida.ENCHENTE_ATE_INICIO_VAZANTE,
            altura_min_m=0.0,
            altura_max_m=1.0,
        )
        assert _tide_phase_match(TidePhase.ENCHENTE, 0.5, mare) == 1.0

    def test_enchente_ate_inicio_vazante_aceita_vazante_perto_do_teto(self) -> None:
        mare = MareIdeal(
            fase_preferida=FasePreferida.ENCHENTE_ATE_INICIO_VAZANTE,
            altura_min_m=0.0,
            altura_max_m=1.0,
        )
        assert _tide_phase_match(TidePhase.VAZANTE, 0.9, mare) == 0.8

    def test_enchente_ate_inicio_vazante_rejeita_vazante_no_fundo(self) -> None:
        mare = MareIdeal(
            fase_preferida=FasePreferida.ENCHENTE_ATE_INICIO_VAZANTE,
            altura_min_m=0.0,
            altura_max_m=1.0,
        )
        assert _tide_phase_match(TidePhase.VAZANTE, 0.1, mare) == 0.2


class TestLevelMatch:
    def test_nivel_dentro_da_faixa_do_pico_eh_match(self) -> None:
        assert _level_match(NivelUsuario.INTERMEDIARIO, Nivel.INTERMEDIARIO_AVANCADO) == 1.0

    def test_nivel_um_degrau_abaixo_penaliza_moderado(self) -> None:
        assert _level_match(NivelUsuario.INICIANTE, Nivel.INTERMEDIARIO) == 0.6

    def test_nivel_muito_abaixo_penaliza_forte(self) -> None:
        assert _level_match(NivelUsuario.INICIANTE, Nivel.AVANCADO) == 0.2


class TestScoreSpot:
    def test_condicoes_ideais_geram_score_alto(self) -> None:
        spot = _spot()
        swell = SwellReading(
            timestamp=datetime(2026, 9, 10, 7, 0), altura_m=1.2, direcao_graus=110, periodo_s=10
        )
        vento = WindReading(
            timestamp=datetime(2026, 9, 10, 7, 0), velocidade_ms=5, direcao_graus=290
        )
        mare = TideReading(
            timestamp=datetime(2026, 9, 10, 7, 0), altura_m=0.5, fase=TidePhase.INDETERMINADA
        )

        resultado = score_spot(spot, swell, vento, mare, NivelUsuario.INTERMEDIARIO)

        assert resultado.score_total > 90
        assert resultado.spot_id == "teste"
        assert len(resultado.fatores) == 4

    def test_condicoes_ruins_geram_score_baixo(self) -> None:
        spot = _spot()
        swell = SwellReading(
            timestamp=datetime(2026, 9, 10, 7, 0), altura_m=0.3, direcao_graus=0, periodo_s=5
        )
        vento = WindReading(
            timestamp=datetime(2026, 9, 10, 7, 0), velocidade_ms=15, direcao_graus=90
        )
        mare = TideReading(
            timestamp=datetime(2026, 9, 10, 7, 0), altura_m=2.0, fase=TidePhase.INDETERMINADA
        )

        resultado = score_spot(spot, swell, vento, mare, NivelUsuario.INICIANTE)

        assert resultado.score_total < 20

    def test_pesos_dos_fatores_somam_um(self) -> None:
        spot = _spot()
        swell = SwellReading(
            timestamp=datetime(2026, 9, 10, 7, 0), altura_m=1.0, direcao_graus=110, periodo_s=9
        )
        vento = WindReading(
            timestamp=datetime(2026, 9, 10, 7, 0), velocidade_ms=5, direcao_graus=290
        )
        mare = TideReading(timestamp=datetime(2026, 9, 10, 7, 0), altura_m=0.5)

        resultado = score_spot(spot, swell, vento, mare, NivelUsuario.INTERMEDIARIO)

        assert sum(f.peso for f in resultado.fatores) == pytest.approx(1.0)
