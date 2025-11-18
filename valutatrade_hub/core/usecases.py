from __future__ import annotations

import secrets
import string
from datetime import datetime
from typing import Any, Dict, List, Tuple

from .models import User
from .utils import (
    PORTFOLIOS_FILE,
    RATES_FILE,
    USERS_FILE,
    load_json,
    save_json,
    validate_currency_code,
    validate_username,
)


def _generate_salt(length: int = 8) -> str:
    """Генерация случайной соли для хеширования пароля."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def register_user(username: str, password: str) -> User:
    """Зарегистрировать нового пользователя.

    Шаги по ТЗ:
    1. Проверить уникальность username в users.json.
    2. Сгенерировать user_id (автоинкремент).
    3. Захешировать пароль (SHA-256(password + salt)).
    4. Сохранить пользователя в users.json.
    5. Создать пустой портфель в portfolios.json.
    """
    username_normalized = validate_username(username)

    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов.")

    users_data: List[Dict[str, Any]] = load_json(USERS_FILE, default=[])

    for record in users_data:
        if record.get("username") == username_normalized:
            raise ValueError(f"Имя пользователя '{username_normalized}' уже занято")

    if users_data:
        max_id = 0
        for record in users_data:
            value = record.get("user_id", 0)
            try:
                candidate = int(value)
            except (TypeError, ValueError):
                candidate = 0
            if candidate > max_id:
                max_id = candidate
        user_id = max_id + 1
    else:
        user_id = 1

    salt = _generate_salt()
    registration_date = datetime.now()

    user = User(
        user_id=user_id,
        username=username_normalized,
        hashed_password="",
        salt=salt,
        registration_date=registration_date,
    )
    user.change_password(password)

    user_record: Dict[str, object] = {
        "user_id": user.user_id,
        "username": user.username,
        "hashed_password": user.hashed_password,
        "salt": user.salt,
        "registration_date": user.registration_date.isoformat(),
    }
    users_data.append(user_record)
    save_json(USERS_FILE, users_data)

    portfolios_data: List[Dict[str, object]] = load_json(PORTFOLIOS_FILE, default=[])
    portfolios_data.append({"user_id": user_id, "wallets": {}})
    save_json(PORTFOLIOS_FILE, portfolios_data)

    return user


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
