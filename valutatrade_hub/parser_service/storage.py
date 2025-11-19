from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ..core.utils import validate_currency_code
from .config import ParserConfig


@dataclass
class ExchangeRateEntry:
    """Одна запись в журнале exchange_rates.json."""

    id: str
    from_currency: str
    to_currency: str
    rate: float
    timestamp: str
    source: str
    meta: Dict[str, Any]


def _normalize_timestamp(ts: datetime | None = None) -> str:
    """Вернуть ISO-строку в UTC без микросекунд, оканчивающуюся на 'Z'."""
    if ts is None:
        ts = datetime.now(timezone.utc)
    ts = ts.astimezone(timezone.utc).replace(microsecond=0)
    return ts.isoformat().replace("+00:00", "Z")


def build_exchange_rate_entry(
    from_currency: str,
    to_currency: str,
    rate: float,
    source: str,
    timestamp: datetime | None = None,
    meta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Сконструировать валидную запись журнала exchange_rates.json.

    Правила:
    - id = <FROM>_<TO>_<ISO-UTC timestamp>, например BTC_USD_2025-10-10T12:00:00Z
    - коды валют приводим к верхнему регистру и валидируем;
    - rate должен быть числом (float);
    - timestamp пишем в ISO-формате UTC с 'Z' на конце.
    """
    from_code = validate_currency_code(from_currency)
    to_code = validate_currency_code(to_currency)

    if not isinstance(rate, (int, float)):
        raise TypeError("rate must be a number.")
    rate_value = float(rate)

    ts_str = _normalize_timestamp(timestamp)
    entry_id = f"{from_code}_{to_code}_{ts_str}"

    if meta is None:
        meta = {}

    entry = ExchangeRateEntry(
        id=entry_id,
        from_currency=from_code,
        to_currency=to_code,
        rate=rate_value,
        timestamp=ts_str,
        source=source,
        meta=meta,
    )
    return asdict(entry)


def _load_all_entries(path: Path) -> List[Dict[str, Any]]:
    """Загрузить все записи из exchange_rates.json.

    При отсутствии файла или ошибке формата — вернуть пустой список.
    """
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return []

    if isinstance(data, list):
        return data
    return []


def _atomic_write(path: Path, data: List[Dict[str, Any]]) -> None:
    """Атомарная запись JSON в файл.

    Пишем во временный файл и затем заменяем основной через os.replace.
    Это гарантирует целостность даже при сбое во время записи.
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def append_exchange_rate_entry(entry: Dict[str, Any]) -> None:
    """Добавить запись в журнал exchange_rates.json, избегая дублей по id.

    - Читаем текущий список записей.
    - Проверяем, что такого id ещё нет.
    - Добавляем запись и атомарно перезаписываем файл.
    """
    config = ParserConfig()
    path = config.exchange_rates_file

    entries = _load_all_entries(path)
    existing_ids = {
        item.get("id")
        for item in entries
        if isinstance(item, dict) and "id" in item
    }

    entry_id = entry.get("id")
    if entry_id in existing_ids:
        # Такой замер уже есть — не дублируем.
        return

    entries.append(entry)
    _atomic_write(path, entries)
