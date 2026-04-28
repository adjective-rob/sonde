from pathlib import Path

APP_NAME = "topicops"
DEFAULT_CONFIG = Path("topics.yaml")
DEFAULT_STATE_DIR = Path(".topicops")
DEFAULT_DB_PATH = DEFAULT_STATE_DIR / "topicops.db"
DEFAULT_ARTIFACT_PATH = DEFAULT_STATE_DIR / "artifacts"
ADAPTER_VERSION = "0.1.0"
KNOWN_SOURCE_IDS = {"github", "arxiv", "huggingface", "rss", "local_jsonl"}
