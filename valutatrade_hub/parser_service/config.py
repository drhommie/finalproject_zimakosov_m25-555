from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ..infra.settings import SettingsLoader


@dataclass(frozen=True)
class ParserConfig:
    """Конфигурация Parser Service.

    EXCHANGERATE_API_KEY — читается из переменной окружения.
    Остальные параметры подтягиваются из SettingsLoader и будут
    расширены на следующих шагах.
    """

    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "")

    # Базовые директории и файлы (читаем из основного SettingsLoader)
    data_dir: Path = SettingsLoader().get("data_dir")
    rates_file: Path = SettingsLoader().get("rates_file")

    # Предварительные параметры: будут расширены в 4.2–4.3
    fiat_base_currency: str = "USD"
    crypto_vs_currency: str = "usd"
