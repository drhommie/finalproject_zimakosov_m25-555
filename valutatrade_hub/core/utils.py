from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Базовая директория проекта: finalproject_*/ (корень репозитория)
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"


def load_json(path: Path, default: Any) -> Any:
    """Загрузить JSON из файла или вернуть default при ошибке."""
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def save_json(path: Path, data: Any) -> None:
    """Сохранить данные в JSON-файл."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def validate_amount(amount: float) -> float:
    """Проверка суммы: число > 0. Возвращает сумму как float."""
    if not isinstance(amount, (int, float)):
        raise TypeError("Сумма должна быть числом.")
    value = float(amount)
    if value <= 0:
        raise ValueError("Сумма должна быть положительной.")
    return value


def validate_currency_code(code: str) -> str:
    """Проверка кода валюты: непустая строка в верхнем регистре."""
    if not isinstance(code, str):
        raise TypeError("Код валюты должен быть строкой.")
    normalized = code.strip().upper()
    if not normalized:
        raise ValueError("Код валюты не может быть пустым.")
    return normalized

def validate_username(username: str) -> str:
    """Проверка имени пользователя: непустая строка без пробелов по краям."""
    if not isinstance(username, str):
        raise TypeError("Имя пользователя должно быть строкой.")
    normalized = username.strip()
    if not normalized:
        raise ValueError("Имя пользователя не может быть пустым.")
    return normalized

