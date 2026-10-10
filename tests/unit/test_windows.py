from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from surfscout.adapters.storage.spots_repo import load_spots
from surfscout.domain.models import SwellReading, TideReading, WindReading
from surfscout.domain.windows import HourReading, Preferences, evaluate_windows

DAY = date(2026, 10, 11)
SPOT = next(s for s in load_spots(Path("src/surfscout/spots.yaml")) if s.id == "matadeiro")


def readings() -> list[HourReading]:
    return [
        HourReading(
            swell=SwellReading(
                timestamp=(at := datetime(2026, 10, 11, h)),
                altura_m=0.8,
                direcao_graus=90,
                periodo_s=8,
            ),
            wind=WindReading(timestamp=at, velocidade_ms=4, direcao_graus=180),
            tide=TideReading(timestamp=at, altura_m=0.4),
        )
        for h in range(10, 14)
    ]


def test_full_windows_not_single_best_point() -> None:
    result = evaluate_windows(SPOT, readings(), DAY, Preferences(spots=["matadeiro"]))
    assert [w.start.hour for w in result.windows] == [10, 11, 12]
    assert all(w.end - w.start == timedelta(minutes=90) for w in result.windows)
    assert max(w.end for w in result.windows) <= datetime(2026, 10, 11, 14)


def test_missing_hour_cannot_be_bridged() -> None:
    values = [r for r in readings() if r.swell.timestamp.hour != 11]
    result = evaluate_windows(SPOT, values, DAY, Preferences(spots=["matadeiro"]))
    assert [w.start.hour for w in result.windows] == [12]


def test_outside_coverage_returns_no_window() -> None:
    assert not evaluate_windows(
        SPOT, readings(), date(2026, 10, 12), Preferences(spots=["matadeiro"])
    ).windows


def test_unknown_personal_travel_does_not_filter() -> None:
    prefs = Preferences(spots=["matadeiro"], travel_max=1)
    assert evaluate_windows(SPOT, readings(), DAY, prefs).eligible
    assert not evaluate_windows(SPOT, readings(), DAY, prefs, travel_minutes=33).eligible


def test_beginner_is_not_sent_to_intermediate_spot() -> None:
    result = evaluate_windows(
        SPOT, readings(), DAY, Preferences(spots=["matadeiro"], level="iniciante")
    )
    assert not result.eligible
    assert "nível" in result.reason


def test_hard_size_applies_to_entire_window() -> None:
    values = readings()
    values[1].swell.altura_m = 1.5
    prefs = Preferences(spots=["matadeiro"], size_max=1, hard_size=True)
    assert [w.start.hour for w in evaluate_windows(SPOT, values, DAY, prefs).windows] == [12]


@pytest.mark.parametrize(
    "data",
    [
        {"start": "13:00", "end": "14:00", "duration": 90},
        {"spots": []},
        {"size_min": 2, "size_max": 1},
        {"hard_size": True},
        {"start": "05:00"},
    ],
)
def test_invalid_preferences(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Preferences.model_validate({"spots": ["matadeiro"], **data})
