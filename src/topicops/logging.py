import logging
import os


def configure_logging() -> None:
    level = os.getenv("TOPICOPS_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
