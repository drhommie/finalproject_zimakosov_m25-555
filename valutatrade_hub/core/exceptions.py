from __future__ import annotations


class CurrencyError(Exception):
    """Базовое исключение для ошибок, связанных с валютами."""


class InsufficientFundsError(CurrencyError):
    """Недостаточно средств на кошельке."""


class CurrencyNotFoundError(CurrencyError):
    """Неизвестная или неподдерживаемая валюта."""


class ApiRequestError(CurrencyError):
    """Ошибка при обращении к внешнему API (Parser Service или заглушка)."""
