from pathlib import Path

import yaml

from surfscout.domain.models import SpotProfile


def load_spots(path: Path) -> list[SpotProfile]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [SpotProfile.model_validate(item) for item in raw]
