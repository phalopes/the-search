"""Authenticated HTTP adapter. Same Python domain as CLI, no privileged API key."""

import asyncio
import json
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode, urlparse

from pydantic import ValidationError
from workers import Response, WorkerEntrypoint, fetch

from surfscout.adapters.weather.hourly import HourlyPayload, parse_hours
from surfscout.domain.models import SpotProfile
from surfscout.domain.windows import Preferences, evaluate_windows

TIMEZONE = timezone(timedelta(hours=-3))


async def request_json(
    url: str, headers: dict[str, str] | None = None, method: str = "GET", body: Any = None
) -> Any:
    """Bound every upstream operation; retry only transient upstream failures."""
    for attempt in range(3):
        try:
            options: dict[str, Any] = {"method": method, "headers": headers or {}}
            if body is not None:
                options["body"] = json.dumps(body)
            response = await asyncio.wait_for(fetch(url, **options), timeout=15)
            if response.status >= 500 and attempt < 2:
                await asyncio.sleep(0.3 * (attempt + 1))
                continue
            if response.status >= 400:
                raise RuntimeError(f"upstream_status_{response.status}")
            text = await response.text()
            return json.loads(text) if text else None
        except TimeoutError:
            if attempt == 2:
                raise
    raise RuntimeError("upstream_unavailable")


class Default(WorkerEntrypoint):
    async def fetch(self, request: Any) -> Any:
        path = urlparse(request.url).path
        if path == "/api/health":
            return self.reply({"ok": True, "engine": "python", "version": "v1"})
        if not path.startswith("/api/"):
            return await self.env.ASSETS.fetch(request)
        if request.method not in ("GET", "POST"):
            return self.reply({"error": "Método não permitido."}, 405)
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return self.reply({"error": "Entre para acessar seu surf."}, 401)
        headers = {
            "Authorization": token,
            "apikey": self.env.SUPABASE_KEY,
            "Content-Type": "application/json",
        }
        base = self.env.SUPABASE_URL
        try:
            user = await request_json(base + "/auth/v1/user", headers)
        except (RuntimeError, TimeoutError):
            return self.reply({"error": "Sessão inválida ou indisponível. Entre novamente."}, 401)
        try:
            members = await request_json(base + "/rest/v1/members?select=admin", headers)
            if not members:
                return self.reply({"error": "Acesso restrito ao piloto pessoal."}, 403)
            if path == "/api/bootstrap":
                spots, profiles, travel = await asyncio.gather(
                    request_json(base + "/rest/v1/surf_spots?select=*&order=id", headers),
                    request_json(base + "/rest/v1/surf_profiles?select=preferences", headers),
                    request_json(base + "/rest/v1/travel_times?select=spot_id,minutes", headers),
                )
                return self.reply(
                    {
                        "spots": spots,
                        "preferences": profiles[0]["preferences"] if profiles else None,
                        "travel": travel,
                        "admin": members[0]["admin"],
                    }
                )
            if path != "/api/recommend" or request.method != "POST":
                return self.reply({"error": "Rota não encontrada."}, 404)
            text = await request.text()
            if len(text) > 12000:
                return self.reply({"error": "Consulta muito grande."}, 413)
            body = json.loads(text)
            prefs = Preferences.model_validate(body.get("preferences"))
            day = date.fromisoformat(body["date"])
            today = datetime.now(TIMEZONE).date()
            if not today <= day <= today + timedelta(days=2):
                return self.reply({"error": "Escolha hoje, amanhã ou depois de amanhã."}, 422)
            spots, travel, cached = await asyncio.gather(
                request_json(base + "/rest/v1/surf_spots?select=*&order=id", headers),
                request_json(base + "/rest/v1/travel_times?select=spot_id,minutes", headers),
                request_json(base + "/rest/v1/forecast_snapshots?select=*", headers),
            )
            travel_map = {r["spot_id"]: r["minutes"] for r in travel}
            cache_map = {r["spot_id"]: r for r in cached}
            if not travel_map:
                prefs.travel_max = None
            selected = [s for s in spots if s["id"] in prefs.spots]
            if len(selected) != len(set(prefs.spots)):
                return self.reply({"error": "Pico não cadastrado."}, 422)

            async def one(row: dict[str, Any]) -> dict[str, Any]:
                spot = SpotProfile.model_validate({**row["profile"], "deslocamento_min": 0})
                now = datetime.now(UTC)
                old = cache_map.get(spot.id)
                payload = None
                collected = now.isoformat()
                if old:
                    age = now - datetime.fromisoformat(old["collected_at"].replace("Z", "+00:00"))
                    if timedelta(0) <= age < timedelta(hours=3):
                        payload = HourlyPayload.model_validate(old["payload"])
                        collected = old["collected_at"]
                try:
                    if payload is None:
                        params = {
                            "latitude": spot.coordenadas.lat,
                            "longitude": spot.coordenadas.lon,
                            "timezone": "America/Sao_Paulo",
                            "forecast_days": 3,
                        }
                        marine_params = {
                            **params,
                            "models": "best_match,gwam",
                            "hourly": (
                                "swell_wave_height,swell_wave_direction,"
                                "swell_wave_period,sea_level_height_msl"
                            ),
                        }
                        wind_params = {
                            **params,
                            "models": "best_match",
                            "hourly": "wind_speed_10m,wind_direction_10m",
                            "wind_speed_unit": "ms",
                        }
                        marine, wind = await asyncio.gather(
                            request_json(
                                "https://marine-api.open-meteo.com/v1/marine?"
                                + urlencode(marine_params)
                            ),
                            request_json(
                                "https://api.open-meteo.com/v1/forecast?" + urlencode(wind_params)
                            ),
                        )
                        payload = HourlyPayload(marine=marine, wind=wind)
                        await request_json(
                            base + "/rest/v1/forecast_snapshots?on_conflict=user_id,spot_id",
                            {**headers, "Prefer": "resolution=merge-duplicates"},
                            "POST",
                            {
                                "user_id": user["id"],
                                "spot_id": spot.id,
                                "collected_at": collected,
                                "payload": payload.model_dump(),
                            },
                        )
                    result = evaluate_windows(
                        spot, parse_hours(payload), day, prefs, travel_map.get(spot.id)
                    )
                    # Today's past buckets must not become a future recommendation.
                    if day == today:
                        local_now = datetime.now(TIMEZONE).replace(tzinfo=None)
                        result.windows = [w for w in result.windows if w.start > local_now]
                        result.eligible = bool(result.windows)
                        if not result.windows:
                            result.reason = "Sem janela futura completa nesta disponibilidade."
                    return {
                        **result.model_dump(mode="json"),
                        "collected_at": collected,
                        "snapshot": payload.model_dump(),
                        "experimental": row["experimental"],
                        "provenance": row["provenance"],
                    }
                except (RuntimeError, TimeoutError, ValueError, KeyError):
                    return {
                        "spot_id": spot.id,
                        "name": spot.nome,
                        "hours": [],
                        "windows": [],
                        "eligible": False,
                        "reason": "Previsão indisponível. Tente novamente.",
                        "collected_at": None,
                        "experimental": row["experimental"],
                        "provenance": row["provenance"],
                    }

            results = await asyncio.gather(*(one(s) for s in selected))
            results.sort(key=lambda r: -(r["windows"][0]["score"] if r["windows"] else -1))
            return self.reply(
                {
                    "date": day.isoformat(),
                    "results": results,
                    "timezone": "America/Sao_Paulo",
                    "source": (
                        "Open-Meteo · swell GWAM · vento best_match · nível do mar best_match"
                    ),
                    "limits": (
                        "Índice de encaixe, não probabilidade. Swell em mar aberto; "
                        "nível do mar relativo ao MSL não equivale à tábua de maré local."
                    ),
                }
            )
        except (ValidationError, ValueError, KeyError, TypeError):
            return self.reply({"error": "Confira data, janela, duração, picos e limites."}, 422)
        except (RuntimeError, TimeoutError):
            return self.reply(
                {"error": "Serviço indisponível. Seus dados salvos continuam no banco."}, 503
            )

    def reply(self, body: Any, status: int = 200) -> Response:
        return Response.json(
            body,
            status=status,
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )
