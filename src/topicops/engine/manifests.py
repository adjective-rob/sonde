from __future__ import annotations

import json
from pathlib import Path

from topicops.models.run import RunManifest


def write_manifest(manifest: RunManifest, artifact_root: Path) -> Path:
    manifest_dir = artifact_root / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_dir / f"{manifest.run.id}.manifest.json"
    path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path
