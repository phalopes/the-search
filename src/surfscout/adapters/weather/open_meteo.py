"""Adapter para Open-Meteo Marine + Weather APIs.

Cuidado documentado no escopo do projeto: omitir o parâmetro `models` pode
fazer a API retornar nulo silenciosamente fora da Europa.

Investigação de 2026-09-17 (docs/validacao/2026-09-17/): comparamos os modelos
de onda disponíveis pra costa de Floripa contra o Surf Guru (validado por 3
sessões reais). `best_match` resolve pra `meteofrance_wave` aqui, que
subestima período de swell de forma consistente (~6.5s vs ~10-11s reais).
`gwam` (DWD Global Wave Model) bateu muito mais perto do real (período ~7.9s,
altura quase idêntica). Por isso pedimos os dois modelos na mesma chamada e
usamos `gwam` pro swell — mas `gwam` não retorna `sea_level_height_msl` (é só
um modelo de onda, sem maré), então a maré continua vindo do `best_match`.
Isso é exatamente o tipo de "nulo silencioso" que o escopo alertava: pedir só
`gwam` sem cruzar com `best_match` teria zerado a maré sem erro nenhum.
"""

import datetime as dt
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from surfscout.domain.models import Coordenadas, SwellReading, TidePhase, TideReading, WindReading

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_MODELS = "best_match,gwam"
WIND_MODEL = "best_match"
SWELL_MODEL_SUFFIX = "gwam"
TIDE_MODEL_SUFFIX = "marine_best_match"
TIMEZONE = "America/Sao_Paulo"
TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return 500 <= exc.response.status_code < 600
    return False


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception(_is_transient),
)
def _get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    response = httpx.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return dict(response.json())


def fetch_marine(coordenadas: Coordenadas, forecast_days: int = 3) -> dict[str, Any]:
    return _get(
        MARINE_URL,
        {
            "latitude": coordenadas.lat,
            "longitude": coordenadas.lon,
            "hourly": (
                "swell_wave_height,swell_wave_direction,swell_wave_period,sea_level_height_msl"
            ),
            "models": MARINE_MODELS,
            "timezone": TIMEZONE,
            "forecast_days": forecast_days,
        },
    )


def fetch_wind(coordenadas: Coordenadas, forecast_days: int = 3) -> dict[str, Any]:
    return _get(
        FORECAST_URL,
        {
            "latitude": coordenadas.lat,
            "longitude": coordenadas.lon,
            "hourly": "wind_speed_10m,wind_direction_10m",
            "wind_speed_unit": "ms",
            "models": WIND_MODEL,
            "timezone": TIMEZONE,
            "forecast_days": forecast_days,
        },
    )


def _nearest_index(times: list[str], target: dt.datetime) -> int:
    parsed = [dt.datetime.fromisoformat(t) for t in times]
    return min(range(len(parsed)), key=lambda i: abs((parsed[i] - target).total_seconds()))


def _tide_phase(alturas: list[float | None], indice: int) -> TidePhase:
    if indice == 0 or alturas[indice] is None or alturas[indice - 1] is None:
        return TidePhase.INDETERMINADA
    atual, anterior = alturas[indice], alturas[indice - 1]
    assert atual is not None and anterior is not None
    if atual > anterior:
        return TidePhase.ENCHENTE
    if atual < anterior:
        return TidePhase.VAZANTE
    return TidePhase.INDETERMINADA


def fetch_readings(
    coordenadas: Coordenadas, at: dt.datetime, forecast_days: int = 3
) -> tuple[SwellReading, WindReading, TideReading]:
    marine = fetch_marine(coordenadas, forecast_days)["hourly"]
    vento = fetch_wind(coordenadas, forecast_days)["hourly"]

    altura_swell = marine[f"swell_wave_height_{SWELL_MODEL_SUFFIX}"]
    direcao_swell = marine[f"swell_wave_direction_{SWELL_MODEL_SUFFIX}"]
    periodo_swell = marine[f"swell_wave_period_{SWELL_MODEL_SUFFIX}"]
    altura_mare = marine[f"sea_level_height_msl_{TIDE_MODEL_SUFFIX}"]

    idx_marine = _nearest_index(marine["time"], at)
    idx_vento = _nearest_index(vento["time"], at)

    timestamp = dt.datetime.fromisoformat(marine["time"][idx_marine])

    swell = SwellReading(
        timestamp=timestamp,
        altura_m=altura_swell[idx_marine],
        direcao_graus=direcao_swell[idx_marine],
        periodo_s=periodo_swell[idx_marine],
    )
    mare = TideReading(
        timestamp=timestamp,
        altura_m=altura_mare[idx_marine],
        fase=_tide_phase(altura_mare, idx_marine),
    )
    vento_reading = WindReading(
        timestamp=dt.datetime.fromisoformat(vento["time"][idx_vento]),
        velocidade_ms=vento["wind_speed_10m"][idx_vento],
        direcao_graus=vento["wind_direction_10m"][idx_vento],
    )
    return swell, vento_reading, mare
