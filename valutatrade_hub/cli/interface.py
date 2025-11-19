from __future__ import annotations

import shlex
from typing import List, Optional

from ..core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from ..core.models import User
from ..core.usecases import (
    buy_currency,
    get_rate_with_cache,
    get_user_portfolio_summary,
    login_user,
    register_user,
    sell_currency,
)

_current_user: Optional[User] = None

def _parse_register_args(args: List[str]) -> tuple[str, str]:
    """Разбор аргументов для команды register."""
    username: str | None = None
    password: str | None = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--username" and i + 1 < len(args):
            username = args[i + 1]
            i += 2
            continue
        if arg == "--password" and i + 1 < len(args):
            password = args[i + 1]
            i += 2
            continue
        raise ValueError(f"Неизвестный аргумент для register: {arg}")
    if username is None:
        raise ValueError("Параметр --username обязателен.")
    if password is None:
        raise ValueError("Параметр --password обязателен.")
    return username, password


def _parse_login_args(args: List[str]) -> tuple[str, str]:
    """Разбор аргументов для команды login."""
    username: str | None = None
    password: str | None = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--username" and i + 1 < len(args):
            username = args[i + 1]
            i += 2
            continue
        if arg == "--password" and i + 1 < len(args):
            password = args[i + 1]
            i += 2
            continue
        raise ValueError(f"Неизвестный аргумент для login: {arg}")
    if username is None:
        raise ValueError("Параметр --username обязателен.")
    if password is None:
        raise ValueError("Параметр --password обязателен.")
    return username, password


def _parse_show_portfolio_args(args: List[str]) -> str:
    """Разбор аргументов для команды show-portfolio."""
    base = "USD"

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--base" and i + 1 < len(args):
            base = args[i + 1]
            i += 2
            continue
        raise ValueError(f"Неизвестный аргумент для show-portfolio: {arg}")
    return base


def _parse_buy_args(args: List[str]) -> tuple[str, float]:
    """Разбор аргументов для команды buy."""
    currency: str | None = None
    amount_str: str | None = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--currency" and i + 1 < len(args):
            currency = args[i + 1]
            i += 2
            continue
        if arg == "--amount" and i + 1 < len(args):
            amount_str = args[i + 1]
            i += 2
            continue
        raise ValueError(f"Неизвестный аргумент для buy: {arg}")

    if currency is None:
        raise ValueError("Параметр --currency обязателен.")
    if amount_str is None:
        raise ValueError("Параметр --amount обязателен.")

    try:
        amount = float(amount_str)
    except ValueError as exc:
        raise ValueError("'amount' должен быть положительным числом") from exc

    return currency, amount


def _parse_sell_args(args: List[str]) -> tuple[str, float]:
    """Разбор аргументов для команды sell."""
    currency: str | None = None
    amount_str: str | None = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--currency" and i + 1 < len(args):
            currency = args[i + 1]
            i += 2
            continue
        if arg == "--amount" and i + 1 < len(args):
            amount_str = args[i + 1]
            i += 2
            continue
        raise ValueError(f"Неизвестный аргумент для sell: {arg}")

    if currency is None:
        raise ValueError("Параметр --currency обязателен.")
    if amount_str is None:
        raise ValueError("Параметр --amount обязателен.")

    try:
        amount = float(amount_str)
    except ValueError as exc:
        raise ValueError("'amount' должен быть положительным числом") from exc

    return currency, amount


def _parse_get_rate_args(args: List[str]) -> tuple[str, str]:
    """Разбор аргументов для команды get-rate."""
    from_code: str | None = None
    to_code: str | None = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--from" and i + 1 < len(args):
            from_code = args[i + 1]
            i += 2
            continue
        if arg == "--to" and i + 1 < len(args):
            to_code = args[i + 1]
            i += 2
            continue
        raise ValueError(f"Неизвестный аргумент для get-rate: {arg}")

    if from_code is None:
        raise ValueError("Параметр --from обязателен.")
    if to_code is None:
        raise ValueError("Параметр --to обязателен.")

    return from_code, to_code


def _handle_register(args: List[str]) -> None:
    """Обработчик команды register."""
    try:
        username, password = _parse_register_args(args)
        user = register_user(username=username, password=password)
        print(
            f"Пользователь '{user.username}' зарегистрирован (id={user.user_id}). "
            f"Войдите: login --username {user.username} --password ****"
        )
    except ValueError as exc:
        # Сообщения об ошибках уже соответствуют ТЗ:
        # - "Имя пользователя 'alice' уже занято"
        # - "Пароль должен быть не короче 4 символов"
        print(str(exc))


def _handle_login(args: List[str]) -> None:
    """Обработчик команды login."""
    global _current_user

    try:
        username, password = _parse_login_args(args)
        user = login_user(username=username, password=password)
        _current_user = user
        print(f"Вы вошли как '{user.username}'")
    except ValueError as exc:
        print(str(exc))


def _handle_show_portfolio(args: List[str]) -> None:
    """Обработчик команды show-portfolio."""
    if _current_user is None:
        print("Сначала выполните login")
        return

    try:
        base_currency = _parse_show_portfolio_args(args)
        rows, total = get_user_portfolio_summary(
            user=_current_user,
            base_currency=base_currency,
        )
        base = base_currency.strip().upper()
        username = _current_user.username

        if not rows:
            print(f"Портфель пользователя '{username}' пуст.")
            return

        print(f"Портфель пользователя '{username}' (база: {base}):")
        for row in rows:
            code = row["currency_code"]
            balance = float(row["balance"])
            value_in_base = float(row["value_in_base"])

            if code in {"BTC", "ETH"}:
                balance_str = f"{balance:.4f}"
            else:
                balance_str = f"{balance:.2f}"

            value_str = f"{value_in_base:,.2f}"
            print(f"- {code}: {balance_str}  → {value_str} {base}")

        print("---------------------------------")
        total_str = f"{total:,.2f}"
        print(f"ИТОГО: {total_str} {base}")
    except ValueError as exc:
        print(str(exc))


def _handle_buy(args: List[str]) -> None:
    """Обработчик команды buy."""
    if _current_user is None:
        print("Сначала выполните login")
        return

    try:
        currency, amount = _parse_buy_args(args)
        result = buy_currency(
            user=_current_user,
            currency_code=currency,
            amount=amount,
            base_currency="USD",
        )

        code = result["currency_code"]
        value = float(result["amount"])
        rate = float(result["rate"])
        base = result["base_currency"]
        old_balance = float(result["old_balance"])
        new_balance = float(result["new_balance"])
        estimated_value = float(result["estimated_value"])

        amount_str = f"{value:.4f}"
        rate_str = f"{rate:,.2f}"
        old_str = f"{old_balance:.4f}"
        new_str = f"{new_balance:.4f}"
        estimated_str = f"{estimated_value:,.2f}"

        print(
            f"Покупка выполнена: {amount_str} {code} по курсу "
            f"{rate_str} {base}/{code}",
        )
        print("Изменения в портфеле:")
        print(f"- {code}: было {old_str} → стало {new_str}")
        print(f"Оценочная стоимость покупки: {estimated_str} {base}")
    except ValueError as exc:
        print(str(exc))


def _handle_sell(args: List[str]) -> None:
    """Обработчик команды sell."""
    if _current_user is None:
        print("Сначала выполните login")
        return

    try:
        currency, amount = _parse_sell_args(args)
        result = sell_currency(
            user=_current_user,
            currency_code=currency,
            amount=amount,
            base_currency="USD",
        )

        code = result["currency_code"]
        value = float(result["amount"])
        base = result["base_currency"]
        old_balance = float(result["old_balance"])
        new_balance = float(result["new_balance"])
        rate = result["rate"]
        estimated_value = result["estimated_value"]

        amount_str = f"{value:.4f}"
        old_str = f"{old_balance:.4f}"
        new_str = f"{new_balance:.4f}"

        if isinstance(rate, (int, float)):
            rate_str = f"{float(rate):,.2f}"
        else:
            rate_str = "N/A"

        print(
            f"Продажа выполнена: {amount_str} {code} по курсу "
            f"{rate_str} {base}/{code}",
        )
        print("Изменения в портфеле:")
        print(f"- {code}: было {old_str} → стало {new_str}")

        if isinstance(estimated_value, (int, float)):
            estimated_str = f"{float(estimated_value):,.2f}"
            print(f"Оценочная выручка: {estimated_str} {base}")
    except InsufficientFundsError as exc:
        # Недостаточно средств → показываем сообщение как есть
        print(str(exc))
    except CurrencyNotFoundError as exc:
        # Неизвестная валюта → предлагаем посмотреть коды
        print(str(exc))
        print(
            "Проверьте код валюты или выполните "
            "get-rate для списка поддерживаемых валют.",
        )
    except ApiRequestError as exc:
        # Проблема с внешним API (Parser Service)
        print(str(exc))
        print(
            "Попробуйте повторить запрос позже или "
            "проверьте подключение к сети.",
        )
    except ValueError as exc:
        # Остальные ошибки валидации (amount и т.п.)
        print(str(exc))


def _handle_get_rate(args: List[str]) -> None:
    """Обработчик команды get-rate."""
    try:
        from_code, to_code = _parse_get_rate_args(args)
        rate, updated_at, reverse_rate = get_rate_with_cache(
            from_currency=from_code,
            to_currency=to_code,
        )

        base = from_code.strip().upper()
        quote = to_code.strip().upper()
        updated_str = updated_at.strftime("%Y-%m-%d %H:%M:%S")

        print(
            f"Курс {base}→{quote}: {rate:.8f} "
            f"(обновлено: {updated_str})",
        )
        print(
            f"Обратный курс {quote}→{base}: "
            f"{reverse_rate:,.2f}",
        )
    except CurrencyNotFoundError as exc:
        print(str(exc))
        print(
            "Проверьте код валюты или выполните "
            "get-rate для списка поддерживаемых валют.",
        )
    except ApiRequestError as exc:
        print(str(exc))
        print(
            "Попробуйте повторить запрос позже или "
            "проверьте подключение к сети.",
        )
    except ValueError as exc:
        # Ошибки формата аргументов и т.п.
        print(str(exc))


def _dispatch_command(command: str, args: List[str]) -> None:
    """Диспетчер команд CLI."""
    if command == "register":
        _handle_register(args)
    elif command == "login":
        _handle_login(args)
    elif command == "show-portfolio":
        _handle_show_portfolio(args)
    elif command == "buy":
        _handle_buy(args)
    elif command == "sell":
        _handle_sell(args)
    elif command == "get-rate":
        _handle_get_rate(args)
    elif command in {"exit", "quit"}:
        print("Выход из ValutaTrade Hub.")
        raise SystemExit
    else:
        print(
            f"Неизвестная команда '{command}'. "
            "Попробуйте: register, login, show-portfolio, buy, sell, get-rate.",
        )


def run_cli() -> None:
    """Основной цикл CLI."""
    print("ValutaTrade Hub CLI. Введите команду или 'exit' для выхода.")
    while True:
        try:
            raw = input("> ").strip()
        except EOFError:
            print()
            break

        if not raw:
            continue

        try:
            parts = shlex.split(raw)
        except ValueError as exc:
            print(f"Ошибка разбора команды: {exc}")
            continue

        command, *arg_tokens = parts
        try:
            _dispatch_command(command, arg_tokens)
        except SystemExit:
            break


