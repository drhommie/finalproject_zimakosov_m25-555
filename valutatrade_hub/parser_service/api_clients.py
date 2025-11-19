from __future__ import annotations

from abc import ABC, abstractmethod
from time import monotonic
from typing import Any, Dict

import requests

from ..core.exceptions import ApiRequestError
from .config import ParserConfig


class BaseApiClient(ABC):
    """Базовый клиент внешнего API.

    Все наследники должны реализовать метод fetch_rates(),
    который возвращает словарь в стандартизованном формате:
    {
        "BTC_USD": 59337.21,
        "ETH_USD": 3720.00,
        ...
    }
    """

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()

    @abstractmethod
    def fetch_rates(self) -> Dict[str, float]:
        """Получить курсы валют в стандартизованном формате."""


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko для получения курсов криптовалют."""

    def fetch_rates(self) -> Dict[str, float]:
        """Запросить курсы криптовалют и вернуть пары вида BTC_USD → rate."""
        cfg = self.config

        ids: list[str] = []
        for code in cfg.CRYPTO_CURRENCIES:
            coin_id = cfg.CRYPTO_ID_MAP.get(code)
            if coin_id:
                ids.append(coin_id)

        if not ids:
            raise ApiRequestError(
                "Не задан ни один корректный ID криптовалюты "
                "для запроса к CoinGecko.",
            )

        params = {
            "ids": ",".join(ids),
            "vs_currencies": cfg.CRYPTO_VS_CURRENCY,
        }

        start = monotonic()
        try:
            response = requests.get(
                cfg.COINGECKO_URL,
                params=params,
                timeout=cfg.REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(
                f"Ошибка при обращении к CoinGecko: {exc}",
            ) from exc
        elapsed_ms = int((monotonic() - start) * 1000)

        if response.status_code != 200:
            raise ApiRequestError(
                "Ошибка CoinGecko: HTTP "
                f"{response.status_code} — {response.text[:200]}",
            )

        try:
            payload: Dict[str, Any] = response.json()
        except ValueError as exc:
            raise ApiRequestError(
                "Некорректный JSON-ответ от CoinGecko.",
            ) from exc

        if not isinstance(payload, dict):
            raise ApiRequestError(
                "Неожиданный формат ответа CoinGecko: ожидался объект JSON.",
            )

        result: Dict[str, float] = {}
        vs_currency = cfg.CRYPTO_VS_CURRENCY.lower()
        base_code = cfg.BASE_FIAT_CURRENCY.upper()

        for code in cfg.CRYPTO_CURRENCIES:
            coin_id = cfg.CRYPTO_ID_MAP.get(code)
            if not coin_id:
                continue

            entry = payload.get(coin_id)
            if not isinstance(entry, dict):
                continue

            rate_value = entry.get(vs_currency)
            if not isinstance(rate_value, (int, float)):
                continue

            pair_key = f"{code}_{base_code}"
            result[pair_key] = float(rate_value)

        if not result:
            raise ApiRequestError(
                "CoinGecko вернул ответ без ожидаемых курсов "
                "для указанных криптовалют.",
            )

        # elapsed_ms пока не используем, но его можно положить в meta позже
        _ = elapsed_ms
        return result


class ExchangeRateApiClient(BaseApiClient):
    """Клиент ExchangeRate-API для получения курсов фиатных валют."""

    def fetch_rates(self) -> Dict[str, float]:
        """Запросить курсы фиатных валют и вернуть пары вида EUR_USD → rate."""
        cfg = self.config

        if not cfg.EXCHANGERATE_API_KEY:
            raise ApiRequestError(
                "Не указан API-ключ для ExchangeRate-API. "
                "Установите переменную окружения EXCHANGERATE_API_KEY.",
            )

        base = cfg.BASE_FIAT_CURRENCY.upper()
        url = f"{cfg.EXCHANGERATE_API_URL}/{cfg.EXCHANGERATE_API_KEY}/latest/{base}"

        start = monotonic()
        try:
            response = requests.get(
                url,
                timeout=cfg.REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(
                f"Ошибка при обращении к ExchangeRate-API: {exc}",
            ) from exc
        elapsed_ms = int((monotonic() - start) * 1000)

        if response.status_code != 200:
            raise ApiRequestError(
                "Ошибка ExchangeRate-API: HTTP "
                f"{response.status_code} — {response.text[:200]}",
            )

        try:
            payload: Dict[str, Any] = response.json()
        except ValueError as exc:
            raise ApiRequestError(
                "Некорректный JSON-ответ от ExchangeRate-API.",
            ) from exc

        if payload.get("result") != "success":
            error_type = payload.get("error-type", "unknown")
            raise ApiRequestError(
                "ExchangeRate-API вернул ошибку: "
                f"{error_type}",
            )

        base_code = str(payload.get("base_code", base)).upper()
        rates = payload.get("rates")
        if not isinstance(rates, dict):
            raise ApiRequestError(
                "Неожиданный формат ответа ExchangeRate-API: "
                "отсутствует секция 'rates'.",
            )

        result: Dict[str, float] = {}
        for code in cfg.FIAT_CURRENCIES:
            raw_rate = rates.get(code)
            if not isinstance(raw_rate, (int, float)):
                continue

            pair_key = f"{code}_{base_code}"
            result[pair_key] = float(raw_rate)

        if not result:
            raise ApiRequestError(
                "ExchangeRate-API вернул ответ без ожидаемых курсов "
                "для указанных фиатных валют.",
            )

        # elapsed_ms пока не используем, но его можно положить в meta позже
        _ = elapsed_ms
        return result

