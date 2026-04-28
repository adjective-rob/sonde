from __future__ import annotations

import json
from pathlib import Path

from topicops.adapters.base import RawSourceRecord
from topicops.models.artifact import Artifact


class ArtifactStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def ensure(self) -> None:
        for path in [
            self.root / "raw",
            self.root / "normalized",
            self.root / "runs",
            self.root / "manifests",
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def write_raw(self, run_id: str, records: list[RawSourceRecord]) -> list[str]:
        self.ensure()
        paths: list[str] = []
        for index, record in enumerate(records, start=1):
            source_dir = self.root / "raw" / record.source
            source_dir.mkdir(parents=True, exist_ok=True)
            path = source_dir / f"{run_id}_{index}.json"
            path.write_text(
                json.dumps(record.model_dump(mode="json"), indent=2, sort_keys=True),
                encoding="utf-8",
            )
            paths.append(str(path))
        return paths

    def append_artifacts(self, artifacts: list[Artifact]) -> Path:
        self.ensure()
        path = self.root / "normalized" / "artifacts.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            for artifact in artifacts:
                handle.write(json.dumps(artifact.model_dump(mode="json"), sort_keys=True) + "\n")
        return path
