from __future__ import annotations

import secrets
import string
from datetime import datetime
from typing import Any, Dict, List, Tuple

from .currencies import get_currency
from .exceptions import ApiRequestError, InsufficientFundsError
from .models import User
from .utils import (
    PORTFOLIOS_FILE,
    RATES_FILE,
    USERS_FILE,
    load_json,
    save_json,
    validate_amount,
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

    user_record: Dict[str, Any] = {
        "user_id": user.user_id,
        "username": user.username,
        "hashed_password": user.hashed_password,
        "salt": user.salt,
        "registration_date": user.registration_date.isoformat(),
    }
    users_data.append(user_record)
    save_json(USERS_FILE, users_data)

    portfolios_data: List[Dict[str, Any]] = load_json(PORTFOLIOS_FILE, default=[])
    portfolios_data.append({"user_id": user_id, "wallets": {}})
    save_json(PORTFOLIOS_FILE, portfolios_data)

    return user


def login_user(username: str, password: str) -> User:
    """Войти в систему по username и паролю.

    Шаги по ТЗ:
    1. Найти пользователя по username.
    2. Сравнить хеш пароля.
    """
    username_normalized = validate_username(username)

    users_data: List[Dict[str, Any]] = load_json(USERS_FILE, default=[])

    for record in users_data:
        if record.get("username") != username_normalized:
            continue

        try:
            user = User(
                user_id=int(record["user_id"]),
                username=str(record["username"]),
                hashed_password=str(record["hashed_password"]),
                salt=str(record["salt"]),
                registration_date=datetime.fromisoformat(
                    str(record["registration_date"]),
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Некорректные данные пользователя в хранилище.") from exc

        if not user.verify_password(password):
            raise ValueError("Неверный пароль")

        return user

    raise ValueError(f"Пользователь '{username_normalized}' не найден")


def get_user_portfolio_summary(
    user: User,
    base_currency: str = "USD",
) -> Tuple[List[Dict[str, Any]], float]:
    """Вернуть сводку портфеля пользователя в базовой валюте.

    Возвращает:
        (rows, total), где
        rows — список словарей с ключами:
            - currency_code
            - balance
            - value_in_base
        total — общая сумма в базовой валюте.
    """
    base = validate_currency_code(base_currency)

    portfolios_data: List[Dict[str, Any]] = load_json(
        PORTFOLIOS_FILE,
        default=[],
    )

    portfolio_record: Dict[str, Any] | None = None
    for record in portfolios_data:
        try:
            if int(record.get("user_id", 0)) == user.user_id:
                portfolio_record = record
                break
        except (TypeError, ValueError):
            continue

    if portfolio_record is None:
        return [], 0.0

    wallets_raw = portfolio_record.get("wallets") or {}
    if not isinstance(wallets_raw, dict) or not wallets_raw:
        return [], 0.0

    rows: List[Dict[str, Any]] = []
    total = 0.0

    for code, info in wallets_raw.items():
        try:
            if isinstance(info, dict):
                balance_val = float(info.get("balance", 0.0))
            else:
                balance_val = float(info)
        except (TypeError, ValueError):
            balance_val = 0.0

        if balance_val == 0.0:
            continue

        cur = validate_currency_code(code)

        if cur == base:
            value_in_base = balance_val
        else:
            try:
                rate, _ = get_rate(cur, base)
            except ValueError as exc:
                raise ValueError(
                    f"Неизвестная базовая валюта '{base}'",
                ) from exc
            value_in_base = balance_val * rate

        rows.append(
            {
                "currency_code": cur,
                "balance": balance_val,
                "value_in_base": value_in_base,
            },
        )
        total += value_in_base

    return rows, total


def buy_currency(
    user: User,
    currency_code: str,
    amount: float,
    base_currency: str = "USD",
) -> Dict[str, Any]:
    """Купить валюту для пользователя.

    Шаги по ТЗ:
    1. Валидировать currency и amount > 0.
    2. Если кошелька нет — создать.
    3. Увеличить баланс кошелька на amount.
    4. Получить курс и оценочную стоимость покупки.
    """
    try:
        value = validate_amount(amount)
    except (TypeError, ValueError) as exc:
        raise ValueError("'amount' должен быть положительным числом") from exc

    code = validate_currency_code(currency_code)
    base = validate_currency_code(base_currency)

    portfolios_data: List[Dict[str, Any]] = load_json(
        PORTFOLIOS_FILE,
        default=[],
    )

    portfolio_record: Dict[str, Any] | None = None
    for record in portfolios_data:
        try:
            if int(record.get("user_id", 0)) == user.user_id:
                portfolio_record = record
                break
        except (TypeError, ValueError):
            continue

    if portfolio_record is None:
        portfolio_record = {"user_id": user.user_id, "wallets": {}}
        portfolios_data.append(portfolio_record)

    wallets_raw = portfolio_record.get("wallets")
    if not isinstance(wallets_raw, dict):
        wallets_raw = {}
        portfolio_record["wallets"] = wallets_raw

    wallet_info = wallets_raw.get(code)
    try:
        if isinstance(wallet_info, dict):
            old_balance = float(wallet_info.get("balance", 0.0))
        else:
            old_balance = float(wallet_info or 0.0)
    except (TypeError, ValueError):
        old_balance = 0.0

    new_balance = old_balance + value
    wallets_raw[code] = {"balance": new_balance}

    save_json(PORTFOLIOS_FILE, portfolios_data)

    try:
        rate, _ = get_rate(code, base)
    except ValueError as exc:
        raise ValueError(f"Не удалось получить курс для {code}→{base}") from exc

    estimated_value = value * rate

    return {
        "currency_code": code,
        "amount": value,
        "rate": rate,
        "base_currency": base,
        "old_balance": old_balance,
        "new_balance": new_balance,
        "estimated_value": estimated_value,
    }


def sell_currency(
    user: User,
    currency_code: str,
    amount: float,
    base_currency: str = "USD",
) -> Dict[str, Any]:
    """Продать указанную валюту пользователя.

    Шаги по ТЗ:
    1. Валидировать входные данные.
    2. Проверить, что кошелёк существует и достаточно средств.
    3. Уменьшить баланс.
    4. Опционально посчитать оценочную выручку в базовой валюте.
    """
    try:
        value = validate_amount(amount)
    except (TypeError, ValueError) as exc:
        raise ValueError("'amount' должен быть положительным числом") from exc

    code = validate_currency_code(currency_code)
    base = validate_currency_code(base_currency)

    portfolios_data: List[Dict[str, Any]] = load_json(
        PORTFOLIOS_FILE,
        default=[],
    )

    portfolio_record: Dict[str, Any] | None = None
    for record in portfolios_data:
        try:
            if int(record.get("user_id", 0)) == user.user_id:
                portfolio_record = record
                break
        except (TypeError, ValueError):
            continue

    if portfolio_record is None:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: она создаётся "
            "автоматически при первой покупке.",
        )

    wallets_raw = portfolio_record.get("wallets")
    if not isinstance(wallets_raw, dict) or code not in wallets_raw:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: она создаётся "
            "автоматически при первой покупке.",
        )

    wallet_info = wallets_raw.get(code)
    try:
        if isinstance(wallet_info, dict):
            old_balance = float(wallet_info.get("balance", 0.0))
        else:
            old_balance = float(wallet_info or 0.0)
    except (TypeError, ValueError):
        old_balance = 0.0

    if old_balance < value:
        raise InsufficientFundsError(
            f"Недостаточно средств: доступно {old_balance:.4f} {code}, "
            f"требуется {value:.4f} {code}",
        )

    new_balance = old_balance - value
    wallets_raw[code] = {"balance": new_balance}

    save_json(PORTFOLIOS_FILE, portfolios_data)

    rate: float | None
    estimated_value: float | None
    try:
        rate, _ = get_rate(code, base)
        estimated_value = value * rate
    except ValueError:
        rate = None
        estimated_value = None

    return {
        "currency_code": code,
        "amount": value,
        "rate": rate,
        "base_currency": base,
        "old_balance": old_balance,
        "new_balance": new_balance,
        "estimated_value": estimated_value,
    }


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
        updated_at = datetime.fromisoformat(str(item["updated_at"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"Курс для пары {pair_key} не найден в rates.json.",
        ) from exc

    return rate, updated_at


def get_rate_with_cache(
    from_currency: str,
    to_currency: str,
    max_age_seconds: int = 300,
) -> Tuple[float, datetime, float]:
    """Получить курс from→to с поддержкой кеша и обратного курса.

    1. Валидируем коды валют.
    2. Пытаемся взять курс из локального кеша rates.json.
       - Если курс свежий (моложе max_age_seconds), используем его.
       - Иначе обновляем метку времени (заглушка Parser Service).
    3. Если есть только обратная пара (BTC_USD при запросе USD→BTC) —
       инвертируем курс.
    4. Возвращаем (rate, updated_at, reverse_rate).
    """
    base = validate_currency_code(from_currency)
    quote = validate_currency_code(to_currency)

    # Валидируем, что такие коды валют вообще поддерживаются реестром
    get_currency(base)
    get_currency(quote)

    data: Dict[str, Any] = load_json(RATES_FILE, default={})

    direct_key = f"{base}_{quote}"
    reverse_key = f"{quote}_{base}"

    rate: float | None = None
    updated_at: datetime | None = None
    used_key: str | None = None

    # 1. Пытаемся найти прямую пару base_quote
    entry = data.get(direct_key)
    if isinstance(entry, dict) and "rate" in entry and "updated_at" in entry:
        try:
            rate = float(entry["rate"])
            updated_at = datetime.fromisoformat(str(entry["updated_at"]))
            used_key = direct_key
        except (TypeError, ValueError):
            rate = None
            updated_at = None

    # 2. Если прямой пары нет — пробуем обратную
    if rate is None or updated_at is None:
        entry_rev = data.get(reverse_key)
        if (
            isinstance(entry_rev, dict)
            and "rate" in entry_rev
            and "updated_at" in entry_rev
        ):
            try:
                raw_rate = float(entry_rev["rate"])
                if raw_rate != 0:
                    rate = 1.0 * (1.0 / raw_rate)
                else:
                    rate = 0.0
                updated_at = datetime.fromisoformat(str(entry_rev["updated_at"]))
                used_key = reverse_key
            except (TypeError, ValueError):
                rate = None
                updated_at = None

    # 3. Если ничего не нашли — считаем, что Parser Service недоступен
    if rate is None or updated_at is None:
        raise ApiRequestError(
            f"Ошибка при обращении к внешнему API: "
            f"Курс {base}→{quote} недоступен. Повторите попытку позже.",
        )

    # 4. Проверяем "свежесть" курса и при необходимости обновляем метку времени
    now = datetime.now()
    try:
        age_seconds = (now - updated_at).total_seconds()
    except TypeError:
        age_seconds = max_age_seconds + 1

    if age_seconds > max_age_seconds and used_key is not None:
        # Заглушка Parser Service: обновляем только updated_at и last_refresh
        new_ts = now.isoformat(timespec="seconds")
        entry_to_update = data.get(used_key)
        if isinstance(entry_to_update, dict):
            entry_to_update["updated_at"] = new_ts
        data["last_refresh"] = new_ts
        data["source"] = "ParserServiceStub"
        save_json(RATES_FILE, data)
        updated_at = now

    # Обратный курс (to→from)
    if rate != 0:
        reverse_rate = 1.0 * (1.0 / rate)
    else:
        reverse_rate = 0.0

    return rate, updated_at, reverse_rate
