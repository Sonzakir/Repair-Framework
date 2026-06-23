import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path


class RunWriter:
    """Creates and writes the three standard artifacts for one evaluation run directory."""

    def __init__(self, run_dir: Path) -> None:
        self._run_dir = run_dir

    @property
    def run_dir(self) -> Path:
        return self._run_dir

    @classmethod
    def create(cls, runs_dir: Path) -> "RunWriter":
        """Create the next run_NNN directory under runs_dir and return a writer for it."""
        runs_dir.mkdir(parents=True, exist_ok=True)
        next_id = 1
        for child in runs_dir.iterdir():
            if not child.is_dir() or not child.name.startswith("run_"):
                continue
            suffix = child.name.removeprefix("run_")
            if suffix.isdigit():
                next_id = max(next_id, int(suffix) + 1)
        run_dir = runs_dir / f"run_{next_id:03d}"
        run_dir.mkdir()
        return cls(run_dir)

    def write_json(self, filename: str, data: dict) -> None:
        (self._run_dir / filename).write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )

    def log(self, message: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        with (self._run_dir / "execution.log").open("a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}] {message}\n")


def serialize_localization_result(result) -> dict:
    """Convert a LocalizationResult to a JSON-safe dict for results.json."""
    return {
        "backend": result.backend,
        "bug": dataclasses.asdict(result.bug),
        "ranked_locations": [dataclasses.asdict(loc) for loc in result.ranked_locations],
        "metadata": _serialize_metadata(result.metadata),
    }


def _serialize_metadata(metadata: dict) -> dict:
    out = {}
    for key, value in metadata.items():
        if key == "all_metrics" and isinstance(value, dict):
            out[key] = {
                metric: [dataclasses.asdict(loc) for loc in locs]
                for metric, locs in value.items()
            }
        else:
            out[key] = value
    return out
