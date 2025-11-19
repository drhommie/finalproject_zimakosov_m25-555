from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .infra.settings import SettingsLoader

_actions_logger: Optional[logging.Logger] = None


def get_actions_logger() -> logging.Logger:
    """Вернуть логгер для доменных операций (BUY/SELL/REGISTER/LOGIN).

    Реализует ленивую инициализацию и использует SettingsLoader
    для получения путей и настроек.
    """
    global _actions_logger

    if _actions_logger is not None:
        return _actions_logger

    settings = SettingsLoader()
    logs_dir = Path(settings.get("logs_dir"))
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / "actions.log"

    logger = logging.getLogger("valutatrade.actions")
    logger.setLevel(settings.get("log_level", "INFO"))

    if not logger.handlers:
        log_format = settings.get(
            "log_format",
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        )
        formatter = logging.Formatter(
            fmt=log_format,
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=1_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    _actions_logger = logger
    return logger
