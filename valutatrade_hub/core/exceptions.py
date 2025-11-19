from __future__ import annotations


class CurrencyError(Exception):
    """Базовое исключение для ошибок, связанных с валютами."""


class CurrencyNotFoundError(CurrencyError):
    """Валюта с указанным кодом не найдена в реестре."""
