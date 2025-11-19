from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict

from .exceptions import CurrencyNotFoundError


@dataclass(frozen=True)
class Currency(ABC):
    """Абстрактная базовая валюта."""

    name: str
    code: str

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("Currency name cannot be empty.")

        code = self.code.strip().upper()
        if not (2 <= len(code) <= 5):
            raise ValueError("Currency code must be 2–5 characters long.")
        if " " in code:
            raise ValueError("Currency code cannot contain spaces.")

        # нормализуем значения в frozen dataclass
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "code", code)

    @abstractmethod
    def get_display_info(self) -> str:
        """Человекочитаемое представление валюты для UI/логов."""


@dataclass(frozen=True)
class FiatCurrency(Currency):
    """Фиатная валюта."""

    issuing_country: str

    def __post_init__(self) -> None:
        super().__post_init__()
        country = self.issuing_country.strip()
        if not country:
            raise ValueError("issuing_country cannot be empty.")
        object.__setattr__(self, "issuing_country", country)

    def get_display_info(self) -> str:
        return (
            f"[FIAT] {self.code} — {self.name} "
            f"(Issuing: {self.issuing_country})"
        )


@dataclass(frozen=True)
class CryptoCurrency(Currency):
    """Криптовалюта."""

    algorithm: str
    market_cap: float

    def __post_init__(self) -> None:
        super().__post_init__()

        algorithm = self.algorithm.strip()
        if not algorithm:
            raise ValueError("algorithm cannot be empty.")

        if not isinstance(self.market_cap, (int, float)):
            raise TypeError("market_cap must be a number.")
        if self.market_cap < 0:
            raise ValueError("market_cap cannot be negative.")

        object.__setattr__(self, "algorithm", algorithm)
        object.__setattr__(self, "market_cap", float(self.market_cap))

    def get_display_info(self) -> str:
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"
        )


# ---------- Реестр валют и фабрика ----------

_CURRENCY_REGISTRY: Dict[str, Currency] = {
    "USD": FiatCurrency(
        name="US Dollar",
        code="USD",
        issuing_country="United States",
    ),
    "EUR": FiatCurrency(
        name="Euro",
        code="EUR",
        issuing_country="Eurozone",
    ),
    "BTC": CryptoCurrency(
        name="Bitcoin",
        code="BTC",
        algorithm="SHA-256",
        market_cap=1.12e12,
    ),
    "ETH": CryptoCurrency(
        name="Ethereum",
        code="ETH",
        algorithm="Ethash",
        market_cap=4.5e11,
    ),
}


def get_currency(code: str) -> Currency:
    """Вернуть объект Currency по её коду.

    Если код неизвестен — бросаем CurrencyNotFoundError.
    """
    if not isinstance(code, str):
        raise TypeError("Currency code must be a string.")

    normalized = code.strip().upper()
    if not normalized:
        raise ValueError("Currency code cannot be empty.")

    try:
        return _CURRENCY_REGISTRY[normalized]
    except KeyError as exc:
        raise CurrencyNotFoundError(
            f"Неизвестная валюта '{normalized}'",
        ) from exc

