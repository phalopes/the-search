"""Validate upstream arrays and align exact timestamps; skip missing buckets."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from surfscout.domain.models import SwellReading, TidePhase, TideReading, WindReading
from surfscout.domain.windows import HourReading


class HourlyPayload(BaseModel):
    marine: dict[str, Any]
    wind: dict[str, Any]


def parse_hours(payload: HourlyPayload) -> list[HourReading]:
    marine, wind = payload.marine["hourly"], payload.wind["hourly"]
    wind_index = {value: i for i, value in enumerate(wind["time"])}
    result = []
    for i, value in enumerate(marine["time"]):
        j = wind_index.get(value)
        if j is None:
            continue
        try:
            at = datetime.fromisoformat(value)
            result.append(
                HourReading(
                    swell=SwellReading(
                        timestamp=at,
                        altura_m=marine["swell_wave_height_gwam"][i],
                        direcao_graus=marine["swell_wave_direction_gwam"][i],
                        periodo_s=marine["swell_wave_period_gwam"][i],
                    ),
                    wind=WindReading(
                        timestamp=at,
                        velocidade_ms=wind["wind_speed_10m"][j],
                        direcao_graus=wind["wind_direction_10m"][j],
                    ),
                    tide=TideReading(
                        timestamp=at,
                        altura_m=marine["sea_level_height_msl_marine_best_match"][i],
                        fase=_tide_phase(marine["sea_level_height_msl_marine_best_match"], i),
                    ),
                )
            )
        except (ValueError, TypeError, IndexError):
            continue
    return result


def _tide_phase(heights: list[float | None], index: int) -> TidePhase:
    if index == 0 or heights[index] is None or heights[index - 1] is None:
        return TidePhase.INDETERMINADA
    current, previous = heights[index], heights[index - 1]
    assert current is not None and previous is not None
    if current > previous:
        return TidePhase.ENCHENTE
    if current < previous:
        return TidePhase.VAZANTE
    return TidePhase.INDETERMINADA
