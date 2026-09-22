from datetime import date, datetime, time
from enum import StrEnum

from pydantic import BaseModel, Field


class Fundo(StrEnum):
    AREIA = "areia"
    LAJE = "laje"
    PEDRA = "pedra"
    MISTO = "misto"


class Nivel(StrEnum):
    """Nível de surfista para quem um pico costuma funcionar bem."""

    INICIANTE = "iniciante"
    INICIANTE_INTERMEDIARIO = "iniciante-intermediario"
    INTERMEDIARIO = "intermediario"
    INTERMEDIARIO_AVANCADO = "intermediario-avancado"
    AVANCADO = "avancado"


class NivelUsuario(StrEnum):
    """Nível do usuário (sempre um valor simples, sem faixas compostas)."""

    INICIANTE = "iniciante"
    INTERMEDIARIO = "intermediario"
    AVANCADO = "avancado"


class FasePreferida(StrEnum):
    ENCHENTE = "enchente"
    VAZANTE = "vazante"
    PREAMAR = "preamar"
    BAIXA_MAR = "baixa-mar"
    ENCHENTE_ATE_INICIO_VAZANTE = "enchente_ate_inicio_vazante"
    SEM_PREFERENCIA_CLARA = "sem_preferencia_clara"


class TidePhase(StrEnum):
    ENCHENTE = "enchente"
    VAZANTE = "vazante"
    INDETERMINADA = "indeterminada"


class Coordenadas(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class SwellIdeal(BaseModel):
    direcao_min_graus: float = Field(ge=0, lt=360)
    direcao_max_graus: float = Field(ge=0, lt=360)
    periodo_min_s: float | None = None
    periodo_max_s: float | None = None


class VentoIdeal(BaseModel):
    direcao_offshore_min_graus: float = Field(ge=0, lt=360)
    direcao_offshore_max_graus: float = Field(ge=0, lt=360)
    velocidade_max_ms: float | None = None


class MareIdeal(BaseModel):
    fase_preferida: FasePreferida
    altura_min_m: float
    altura_max_m: float


class TamanhoIdeal(BaseModel):
    altura_min_m: float
    altura_max_m: float


class SpotProfile(BaseModel):
    id: str
    nome: str
    regiao: str
    coordenadas: Coordenadas
    fundo: Fundo
    nivel: Nivel
    deslocamento_min: int = Field(ge=0)
    swell_ideal: SwellIdeal
    vento_ideal: VentoIdeal
    mare_ideal: MareIdeal
    tamanho_ideal: TamanhoIdeal
    notas: str = ""


class SwellReading(BaseModel):
    timestamp: datetime
    altura_m: float = Field(ge=0)
    direcao_graus: float = Field(ge=0, lt=360)
    periodo_s: float = Field(ge=0)


class WindReading(BaseModel):
    timestamp: datetime
    velocidade_ms: float = Field(ge=0)
    direcao_graus: float = Field(ge=0, lt=360)


class TideReading(BaseModel):
    timestamp: datetime
    altura_m: float
    fase: TidePhase = TidePhase.INDETERMINADA


class FatorScore(BaseModel):
    nome: str
    peso: float
    valor: float = Field(ge=0, le=1)
    explicacao: str

    @property
    def contribuicao(self) -> float:
        return self.peso * self.valor


class ScoreResult(BaseModel):
    spot_id: str
    spot_nome: str
    timestamp: datetime
    fatores: list[FatorScore]

    @property
    def score_total(self) -> float:
        return round(sum(fator.contribuicao for fator in self.fatores) * 100, 1)


class TipoRegistro(StrEnum):
    SESSAO_REAL = "sessao_real"
    JULGAMENTO_PRE_SESSAO = "julgamento_pre_sessao"


class RegistroValidacao(BaseModel):
    """Uma entrada do histórico de validação manual (Fase 0/1): o que você viveu
    de verdade vs. o que o sistema recomendou, pra comparar depois."""

    id: int | None = None
    data: date
    horario: time | None = None
    pico_id: str
    tipo: TipoRegistro = TipoRegistro.SESSAO_REAL
    nota: float | None = Field(default=None, ge=1, le=5)
    observacao: str = ""
    pico_recomendado: str | None = None
    score_recomendado: float | None = None
    score_pico_escolhido: float | None = None
    criado_em: datetime = Field(default_factory=datetime.now)
