from __future__ import annotations

import hashlib
import json
import re
from typing import Any


def normalize_text(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip())
    normalized = normalized.strip("\"'")
    return normalized.lower()


def slugify_topic_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower())
    slug = re.sub(r"_+", "_", slug)
    return slug.strip("_")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def sha256_digest(value: bytes | str) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def hash_canonical(value: Any) -> str:
    return sha256_digest(canonical_json(value))
