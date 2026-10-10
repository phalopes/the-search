from surfscout.adapters.weather.hourly import HourlyPayload, parse_hours


def test_exact_time_alignment_and_missing_values() -> None:
    marine = {
        "hourly": {
            "time": ["2026-10-11T10:00", "2026-10-11T11:00", "2026-10-11T12:00"],
            "swell_wave_height_gwam": [0.8, None, 0.9],
            "swell_wave_direction_gwam": [90, 90, 90],
            "swell_wave_period_gwam": [8, 8, 8],
            "sea_level_height_msl_marine_best_match": [0.3, 0.4, 0.5],
        }
    }
    wind = {
        "hourly": {
            "time": ["2026-10-11T11:00", "2026-10-11T12:00"],
            "wind_speed_10m": [2, 3],
            "wind_direction_10m": [180, 181],
        }
    }
    result = parse_hours(HourlyPayload(marine=marine, wind=wind))
    assert len(result) == 1
    assert result[0].swell.timestamp.hour == 12
    assert result[0].wind.velocidade_ms == 3
    assert result[0].tide.fase.value == "enchente"
