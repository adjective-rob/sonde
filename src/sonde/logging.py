import logging
import os


def configure_logging() -> None:
    level = os.getenv("SONDE_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
