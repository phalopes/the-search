"""Personal windows over exact hourly forecast buckets, without extrapolation."""

import math
from datetime import date, datetime, time, timedelta

from pydantic import BaseModel, Field, model_validator

from surfscout.domain.models import (
    NivelUsuario,
    ScoreResult,
    SpotProfile,
    SwellReading,
    TideReading,
    WindReading,
)
from surfscout.domain.scoring import score_spot


class Preferences(BaseModel):
    level: NivelUsuario = NivelUsuario.INTERMEDIARIO
    start: time = time(10)
    end: time = time(14)
    duration: int = Field(default=90, ge=60, le=240)
    spots: list[str] = Field(min_length=1, max_length=20)
    size_min: float | None = Field(default=None, ge=0, le=10)
    size_max: float | None = Field(default=None, ge=0, le=10)
    hard_size: bool = False
    travel_max: int | None = Field(default=None, ge=1, le=600)

    @model_validator(mode="after")
    def coherent(self) -> "Preferences":
        a, b = self.start, self.end
        minutes = (b.hour * 60 + b.minute) - (a.hour * 60 + a.minute)
        if a < time(6) or b > time(18) or minutes < self.duration:
            raise ValueError("Use uma janela entre 06h e 18h que comporte a duração mínima.")
        if (
            self.size_min is not None
            and self.size_max is not None
            and self.size_min > self.size_max
        ):
            raise ValueError("A ondulação mínima deve ser menor ou igual à máxima.")
        if self.hard_size and self.size_min is None and self.size_max is None:
            raise ValueError("Defina ao menos um limite de ondulação.")
        return self


class HourReading(BaseModel):
    swell: SwellReading
    wind: WindReading
    tide: TideReading


class HourScore(BaseModel):
    at: datetime
    swell_m: float
    period_s: float
    swell_direction: float
    wind_kmh: float
    wind_direction: float
    sea_level_m: float
    phase: str
    score: float
    factors: ScoreResult


class Window(BaseModel):
    start: datetime
    end: datetime
    score: float
    technical_score: float


class SpotWindows(BaseModel):
    spot_id: str
    name: str
    hours: list[HourScore]
    windows: list[Window]
    eligible: bool
    reason: str = ""


def evaluate_windows(
    spot: SpotProfile,
    readings: list[HourReading],
    day: date,
    prefs: Preferences,
    travel_minutes: int | None = None,
) -> SpotWindows:
    minimum = {
        "iniciante": 1,
        "iniciante-intermediario": 1,
        "intermediario": 2,
        "intermediario-avancado": 2,
        "avancado": 3,
    }[spot.nivel.value]
    user = {"iniciante": 1, "intermediario": 2, "avancado": 3}[prefs.level.value]
    hours = []
    valid = {}
    for reading in readings:
        at = reading.swell.timestamp
        if at.date() != day:
            continue
        result = score_spot(spot, reading.swell, reading.wind, reading.tide, prefs.level)
        hours.append(
            HourScore(
                at=at,
                swell_m=reading.swell.altura_m,
                period_s=reading.swell.periodo_s,
                swell_direction=reading.swell.direcao_graus,
                wind_kmh=round(reading.wind.velocidade_ms * 3.6, 1),
                wind_direction=reading.wind.direcao_graus,
                sea_level_m=reading.tide.altura_m,
                phase=reading.tide.fase.value,
                score=result.score_total,
                factors=result,
            )
        )
        valid[at] = result.score_total, reading.swell.altura_m
    reason = ""
    if user < minimum:
        reason = "Perfil do pico acima do nível informado."
    if (
        prefs.travel_max is not None
        and travel_minutes is not None
        and travel_minutes > prefs.travel_max
    ):
        reason = "Acima do seu limite pessoal de deslocamento."
    windows = []
    lower = datetime.combine(day, prefs.start)
    upper = datetime.combine(day, prefs.end)
    for start in sorted(valid):
        end = start + timedelta(minutes=prefs.duration)
        if reason or start < lower or end > upper:
            continue
        buckets = [start + timedelta(hours=i) for i in range(math.ceil(prefs.duration / 60))]
        if any(at not in valid for at in buckets):
            continue
        weights = [min(60, prefs.duration - i * 60) for i in range(len(buckets))]
        size_fit = [
            (prefs.size_min is None or valid[at][1] >= prefs.size_min)
            and (prefs.size_max is None or valid[at][1] <= prefs.size_max)
            for at in buckets
        ]
        if prefs.hard_size and not all(size_fit):
            continue
        technical = sum(valid[at][0] * w for at, w in zip(buckets, weights, strict=True))
        technical /= prefs.duration
        fit = sum(w for w, fits in zip(weights, size_fit, strict=True) if fits) / prefs.duration
        score = technical
        if prefs.size_min is not None or prefs.size_max is not None:
            score = technical * 0.9 + fit * 10
        windows.append(
            Window(start=start, end=end, score=round(score, 1), technical_score=round(technical, 1))
        )
    windows.sort(key=lambda w: (-w.score, w.start))
    if not reason and not windows:
        reason = "Sem janela completa com dados e limites informados."
    return SpotWindows(
        spot_id=spot.id,
        name=spot.nome,
        hours=hours,
        windows=windows,
        eligible=bool(windows),
        reason=reason,
    )
