"""Logging estructurado JSON para el Bridge."""

import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("miwayki.bridge")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger


log = setup_logging()
