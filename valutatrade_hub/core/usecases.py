from __future__ import annotations

from datetime import datetime
from typing import Tuple

from .utils import RATES_FILE, load_json, validate_currency_code


def get_rate(base_currency: str, quote_currency: str) -> Tuple[float, datetime]:
    """Получить курс base_currency к quote_currency из локального кеша rates.json.

    Ожидается, что в rates.json ключи имеют вид "EUR_USD", "BTC_USD" и т.п.
    Возвращает кортеж (rate, updated_at).
    """
    base = validate_currency_code(base_currency)
    quote = validate_currency_code(quote_currency)

    pair_key = f"{base}_{quote}"
    data = load_json(RATES_FILE, default={})

    try:
        item = data[pair_key]
        rate = float(item["rate"])
        updated_at = datetime.fromisoformat(item["updated_at"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Курс для пары {pair_key} не найден в rates.json.") from exc

    return rate, updated_at
