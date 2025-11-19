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


def _atomic_write(path: Path, data: Any) -> None:
    """Атомарная запись JSON в файл.

    Работает и со списками, и со словарями.
    Пишем во временный файл и затем заменяем основной через os.replace.
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

def _parse_iso_timestamp(value: str) -> datetime:
    """Распарсить ISO-строку с возможным суффиксом 'Z' в datetime (UTC)."""
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def load_rates_snapshot() -> Dict[str, Any]:
    """Загрузить текущий снимок курсов из rates.json.

    Ожидаемый формат:
    {
      "pairs": {
        "EUR_USD": {
          "rate": 1.0786,
          "updated_at": "2025-10-10T12:00:00Z",
          "source": "ExchangeRate-API"
        },
        "BTC_USD": {
          "rate": 59337.21,
          "updated_at": "2025-10-10T12:00:00Z",
          "source": "CoinGecko"
        }
      },
      "last_refresh": "2025-10-10T12:00:01Z"
    }

    При отсутствии файла или некорректном формате возвращается
    словарь с пустым "pairs" и last_refresh=None.
    """
    config = ParserConfig()
    path = config.rates_file

    if not path.exists():
        return {"pairs": {}, "last_refresh": None}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return {"pairs": {}, "last_refresh": None}

    if not isinstance(data, dict):
        return {"pairs": {}, "last_refresh": None}

    pairs = data.get("pairs", {})
    last_refresh = data.get("last_refresh")

    if not isinstance(pairs, dict):
        pairs = {}

    return {"pairs": pairs, "last_refresh": last_refresh}


def update_rates_snapshot_from_entries(
    entries: List[Dict[str, Any]],
) -> None:
    """Обновить снимок текущих курсов в rates.json на основе журнала.

    Правила:
    - для каждой пары (FROM_TO) храним только самый свежий курс;
    - обновление побеждает, если updated_at (timestamp из entry) новее;
    - поле last_refresh = максимальный updated_at среди всех пар;
    - запись выполняется атомарно (через временный файл).
    """
    snapshot = load_rates_snapshot()
    pairs: Dict[str, Any] = snapshot.get("pairs", {}) or {}

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        from_code = entry.get("from_currency")
        to_code = entry.get("to_currency")
        rate = entry.get("rate")
        ts_str = entry.get("timestamp")
        source = entry.get("source")

        if not isinstance(from_code, str) or not isinstance(to_code, str):
            continue
        if not isinstance(rate, (int, float)):
            continue
        if not isinstance(ts_str, str):
            continue
        if not isinstance(source, str):
            continue

        try:
            from_code_norm = validate_currency_code(from_code)
            to_code_norm = validate_currency_code(to_code)
            new_ts = _parse_iso_timestamp(ts_str)
        except Exception:  # noqa: BLE001
            # Некорректные данные пропускаем, не портим кэш.
            continue

        pair_key = f"{from_code_norm}_{to_code_norm}"
        existing = pairs.get(pair_key)

        if isinstance(existing, dict) and "updated_at" in existing:
            try:
                existing_ts = _parse_iso_timestamp(
                    str(existing["updated_at"]),
                )
            except Exception:  # noqa: BLE001
                existing_ts = None
        else:
            existing_ts = None

        # Обновляем, если не было значения или новое свежее.
        if existing_ts is None or new_ts > existing_ts:
            pairs[pair_key] = {
                "rate": float(rate),
                "updated_at": ts_str,
                "source": source,
            }

    # Пересчитываем last_refresh как максимум по updated_at всех пар.
    latest_ts: datetime | None = None
    for value in pairs.values():
        if isinstance(value, dict) and "updated_at" in value:
            ts_raw = value["updated_at"]
            if not isinstance(ts_raw, str):
                continue
            try:
                ts = _parse_iso_timestamp(ts_raw)
            except Exception:  # noqa: BLE001
                continue
            if latest_ts is None or ts > latest_ts:
                latest_ts = ts

    if latest_ts is not None:
        last_refresh = _normalize_timestamp(latest_ts)
    else:
        last_refresh = None

    data_to_write = {
        "pairs": pairs,
        "last_refresh": last_refresh,
    }

    config = ParserConfig()
    _atomic_write(config.rates_file, data_to_write)
