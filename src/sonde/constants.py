from pathlib import Path

APP_NAME = "sonde"
DEFAULT_CONFIG = Path("topics.yaml")
DEFAULT_STATE_DIR = Path(".sonde")
DEFAULT_DB_PATH = DEFAULT_STATE_DIR / "sonde.db"
DEFAULT_ARTIFACT_PATH = DEFAULT_STATE_DIR / "artifacts"
ADAPTER_VERSION = "0.1.0"
KNOWN_SOURCE_IDS = {"github", "arxiv", "huggingface", "rss", "local_jsonl"}
