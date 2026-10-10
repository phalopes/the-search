"""Bundle the same pure domain used by CLI; generated files are never edited."""

import shutil
from pathlib import Path

root = Path(__file__).resolve().parent.parent
target = root / "worker/src/surfscout"
target.mkdir(parents=True, exist_ok=True)
(target / "__init__.py").write_text("")
shutil.copytree(root / "src/surfscout/domain", target / "domain", dirs_exist_ok=True)
for folder in ["adapters", "adapters/weather"]:
    path = target / folder
    path.mkdir(exist_ok=True)
    (path / "__init__.py").write_text("")
shutil.copy(root / "src/surfscout/adapters/weather/hourly.py", target / "adapters/weather")
