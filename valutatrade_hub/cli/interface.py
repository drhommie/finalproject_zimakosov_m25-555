from __future__ import annotations

import shlex
from typing import List, Optional

from ..core.models import User
from ..core.usecases import (
    buy_currency,
    get_user_portfolio_summary,
    login_user,
    register_user,
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


