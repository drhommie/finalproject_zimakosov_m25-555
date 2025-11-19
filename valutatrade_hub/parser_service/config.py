from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from ..infra.settings import SettingsLoader

# Соответствия тикер → ID монеты в CoinGecko.
# Эти ID используются в запросе:
# https://api.coingecko.com/api/v3/simple/price
CRYPTO_ID_MAP: Dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
}


@dataclass(frozen=True)
class ParserConfig:
    """Конфигурация Parser Service.

    Здесь фиксируем:
    - EXCHANGERATE_API_KEY: ключ для ExchangeRate-API (берём из окружения);
    - data_dir / rates_file: пути к данным (из SettingsLoader);
    - fiat_base_currency: базовая валюта для фиатных курсов (USD);
    - crypto_vs_currency: в какой валюте запрашиваем крипту (usd);
    - coingecko_base_url: базовый URL CoinGecko;
    - exchangerate_base_url: базовый URL ExchangeRate-API;
    - fiat_currencies: список фиатных валют, курсы которых нам нужны.
    """

    # Ключ для ExchangeRate-API, читается из переменной окружения.
    # default="" гарантирует, что тип всегда str, без None.
    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "")

    # Пути к данным (из основного конфигуратора SettingsLoader).
    data_dir: Path = SettingsLoader().get("data_dir")
    rates_file: Path = SettingsLoader().get("rates_file")

    # Фиатная базовая валюта и валюта для крипты.
    fiat_base_currency: str = "USD"
    crypto_vs_currency: str = "usd"

    # Базовые URL-ы для внешних API.
    coingecko_base_url: str = "https://api.coingecko.com/api/v3/simple/price"
    exchangerate_base_url: str = "https://v6.exchangerate-api.com/v6"

    # Какие фиатные валюты нас интересуют относительно USD.
    # Из ответа ExchangeRate-API будем сохранять:
    # - from_currency (например, 'EUR')
    # - to_currency (например, 'USD')
    # - rate
    # - timestamp
    # - source='ExchangeRate-API'
    fiat_currencies: tuple[str, ...] = ("EUR", "GBP", "RUB")
