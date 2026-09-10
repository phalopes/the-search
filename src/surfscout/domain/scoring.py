"""Motor de score: função pura, sem I/O.

Cada fator é calculado como um valor 0-1 ("quão bem casa") e combinado por
pesos fixos em um score final 0-100. O objetivo é ser determinístico e
explicável — cada `FatorScore` carrega o motivo em texto, não só o número.
"""

from surfscout.domain.models import (
    FasePreferida,
    FatorScore,
    MareIdeal,
    Nivel,
    NivelUsuario,
    ScoreResult,
    SpotProfile,
    SwellReading,
    TidePhase,
    TideReading,
    WindReading,
)

PESO_SWELL = 0.4
PESO_VENTO = 0.3
PESO_MARE = 0.2
PESO_TAMANHO_NIVEL = 0.1

_TOLERANCIA_DIRECAO_GRAUS = 20.0
_TOLERANCIA_PERIODO_S = 3.0
_TOLERANCIA_ALTURA_MARE_M = 0.3
_TOLERANCIA_ALTURA_TAMANHO_M = 0.4
_TOLERANCIA_VENTO_MS = 4.0

_NIVEL_SPOT_ORDINAL: dict[Nivel, tuple[int, int]] = {
    Nivel.INICIANTE: (1, 1),
    Nivel.INICIANTE_INTERMEDIARIO: (1, 2),
    Nivel.INTERMEDIARIO: (2, 2),
    Nivel.INTERMEDIARIO_AVANCADO: (2, 3),
    Nivel.AVANCADO: (3, 3),
}

_NIVEL_USUARIO_ORDINAL: dict[NivelUsuario, int] = {
    NivelUsuario.INICIANTE: 1,
    NivelUsuario.INTERMEDIARIO: 2,
    NivelUsuario.AVANCADO: 3,
}


def _angular_distance(a: float, b: float) -> float:
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def _direction_match(direcao: float, minimo: float, maximo: float) -> float:
    """1.0 dentro do range [minimo, maximo] (trata range que cruza o 0/360),
    decaindo linearmente até 0 em `_TOLERANCIA_DIRECAO_GRAUS` fora dele."""
    direcao, lo, hi = direcao % 360, minimo % 360, maximo % 360
    dentro = lo <= direcao <= hi if lo <= hi else (direcao >= lo or direcao <= hi)
    if dentro:
        return 1.0
    distancia = min(_angular_distance(direcao, lo), _angular_distance(direcao, hi))
    return max(0.0, 1.0 - distancia / _TOLERANCIA_DIRECAO_GRAUS)


def _period_match(periodo_s: float, minimo: float | None, maximo: float | None) -> float:
    """Período é um "piso" (e às vezes teto) de qualidade, não uma faixa dura."""
    if minimo is not None and periodo_s < minimo:
        return max(0.0, 1.0 - (minimo - periodo_s) / _TOLERANCIA_PERIODO_S)
    if maximo is not None and periodo_s > maximo:
        return max(0.0, 1.0 - (periodo_s - maximo) / _TOLERANCIA_PERIODO_S)
    return 1.0


def _range_match(valor: float, minimo: float, maximo: float, tolerancia: float) -> float:
    if minimo <= valor <= maximo:
        return 1.0
    deficit = minimo - valor if valor < minimo else valor - maximo
    return max(0.0, 1.0 - deficit / tolerancia)


def _speed_cap_match(velocidade_ms: float, maximo: float | None) -> float:
    if maximo is None or velocidade_ms <= maximo:
        return 1.0
    return max(0.0, 1.0 - (velocidade_ms - maximo) / _TOLERANCIA_VENTO_MS)


def _tide_phase_match(fase_atual: TidePhase, altura_m: float, mare: MareIdeal) -> float:
    preferida = mare.fase_preferida
    if preferida == FasePreferida.SEM_PREFERENCIA_CLARA:
        return 1.0
    if fase_atual == TidePhase.INDETERMINADA:
        return 0.7  # não penaliza pesado por incerteza, mas não é match confirmado

    faixa = mare.altura_max_m - mare.altura_min_m
    perto_do_teto = faixa <= 0 or (altura_m - mare.altura_min_m) / faixa >= 0.7
    perto_do_fundo = faixa <= 0 or (altura_m - mare.altura_min_m) / faixa <= 0.3

    if preferida == FasePreferida.ENCHENTE:
        return 1.0 if fase_atual == TidePhase.ENCHENTE else 0.3
    if preferida == FasePreferida.VAZANTE:
        return 1.0 if fase_atual == TidePhase.VAZANTE else 0.3
    if preferida == FasePreferida.PREAMAR:
        return 1.0 if perto_do_teto else 0.3
    if preferida == FasePreferida.BAIXA_MAR:
        return 1.0 if perto_do_fundo else 0.3
    if preferida == FasePreferida.ENCHENTE_ATE_INICIO_VAZANTE:
        if fase_atual == TidePhase.ENCHENTE:
            return 1.0
        return 0.8 if perto_do_teto else 0.2  # vazante recém-começada ainda perto da preamar
    return 1.0


def _level_match(nivel_usuario: NivelUsuario, nivel_spot: Nivel) -> float:
    usuario = _NIVEL_USUARIO_ORDINAL[nivel_usuario]
    minimo, maximo = _NIVEL_SPOT_ORDINAL[nivel_spot]
    if minimo <= usuario <= maximo:
        return 1.0
    distancia = minimo - usuario if usuario < minimo else usuario - maximo
    return 0.6 if distancia == 1 else 0.2


def score_spot(
    spot: SpotProfile,
    swell: SwellReading,
    vento: WindReading,
    mare: TideReading,
    nivel_usuario: NivelUsuario,
) -> ScoreResult:
    swell_direcao = _direction_match(
        swell.direcao_graus, spot.swell_ideal.direcao_min_graus, spot.swell_ideal.direcao_max_graus
    )
    swell_periodo = _period_match(
        swell.periodo_s, spot.swell_ideal.periodo_min_s, spot.swell_ideal.periodo_max_s
    )
    swell_valor = swell_direcao * swell_periodo

    vento_direcao = _direction_match(
        vento.direcao_graus,
        spot.vento_ideal.direcao_offshore_min_graus,
        spot.vento_ideal.direcao_offshore_max_graus,
    )
    vento_velocidade = _speed_cap_match(vento.velocidade_ms, spot.vento_ideal.velocidade_max_ms)
    vento_valor = vento_direcao * vento_velocidade

    mare_altura = _range_match(
        mare.altura_m,
        spot.mare_ideal.altura_min_m,
        spot.mare_ideal.altura_max_m,
        _TOLERANCIA_ALTURA_MARE_M,
    )
    mare_fase = _tide_phase_match(mare.fase, mare.altura_m, spot.mare_ideal)
    mare_valor = (mare_altura + mare_fase) / 2

    tamanho_altura = _range_match(
        swell.altura_m,
        spot.tamanho_ideal.altura_min_m,
        spot.tamanho_ideal.altura_max_m,
        _TOLERANCIA_ALTURA_TAMANHO_M,
    )
    tamanho_nivel = _level_match(nivel_usuario, spot.nivel)
    tamanho_valor = (tamanho_altura + tamanho_nivel) / 2

    fatores = [
        FatorScore(
            nome="swell",
            peso=PESO_SWELL,
            valor=swell_valor,
            explicacao=(
                f"direção {swell.direcao_graus:.0f}° "
                f"(ideal {spot.swell_ideal.direcao_min_graus:.0f}-"
                f"{spot.swell_ideal.direcao_max_graus:.0f}°) × período {swell.periodo_s:.0f}s"
            ),
        ),
        FatorScore(
            nome="vento",
            peso=PESO_VENTO,
            valor=vento_valor,
            explicacao=(
                f"direção {vento.direcao_graus:.0f}° (offshore ideal "
                f"{spot.vento_ideal.direcao_offshore_min_graus:.0f}-"
                f"{spot.vento_ideal.direcao_offshore_max_graus:.0f}°) "
                f"a {vento.velocidade_ms:.1f}m/s"
            ),
        ),
        FatorScore(
            nome="maré",
            peso=PESO_MARE,
            valor=mare_valor,
            explicacao=(
                f"{mare.altura_m:.2f}m em {mare.fase.value} "
                f"(ideal {spot.mare_ideal.altura_min_m:.2f}-{spot.mare_ideal.altura_max_m:.2f}m, "
                f"fase preferida: {spot.mare_ideal.fase_preferida.value})"
            ),
        ),
        FatorScore(
            nome="tamanho×nível",
            peso=PESO_TAMANHO_NIVEL,
            valor=tamanho_valor,
            explicacao=(
                f"onda {swell.altura_m:.1f}m (ideal {spot.tamanho_ideal.altura_min_m:.1f}-"
                f"{spot.tamanho_ideal.altura_max_m:.1f}m) para nível {nivel_usuario.value} "
                f"(pico é {spot.nivel.value})"
            ),
        ),
    ]

    return ScoreResult(
        spot_id=spot.id, spot_nome=spot.nome, timestamp=swell.timestamp, fatores=fatores
    )
