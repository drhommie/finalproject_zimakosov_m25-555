from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from ..infra.settings import SettingsLoader


@dataclass(frozen=True)
class ParserConfig:
    """
    Конфигурация Parser Service — единая точка всех изменяемых параметров.

    Требования по ТЗ:
    - API-ключи не хранятся в коде → загружаются из окружения.
    - Полные URL для запросов к CoinGecko и ExchangeRate-API.
    - Списки валют и отображения для CoinGecko.
    - Параметры запросов (таймаут, базовая валюта).
    - Пути к файлам data/rates.json и data/exchange_rates.json.
    """

    # -----------------------------
    # 1. API ключи (из окружения)
    # -----------------------------
    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "")

    # -----------------------------
    # 2. Эндпоинты внешних API
    # -----------------------------
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # ----------------------------------
    # 3. Наборы валют для отслеживания
    # ----------------------------------
    BASE_FIAT_CURRENCY: str = "USD"      # базовая валюта фиата
    CRYPTO_VS_CURRENCY: str = "usd"      # "vs_currencies" для CoinGecko

    FIAT_CURRENCIES: Tuple[str, ...] = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: Tuple[str, ...] = ("BTC", "ETH", "SOL")

    # Отображение тикер → CoinGecko ID
    CRYPTO_ID_MAP: Dict[str, str] = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
    }

    # -----------------------------
    # 4. Пути к файлам данных
    # -----------------------------
    data_dir: Path = SettingsLoader().get("data_dir")
    rates_file: Path = SettingsLoader().get("rates_file")  # data/rates.json
    exchange_rates_file: Path = data_dir / "exchange_rates.json"

    # -----------------------------
    # 5. Сетевые параметры
    # -----------------------------
    REQUEST_TIMEOUT: int = 10  # сек. ожидания ответа API

