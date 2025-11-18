from __future__ import annotations

import shlex
from typing import List

from ..core.usecases import register_user


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


def _dispatch_command(command: str, args: List[str]) -> None:
    """Диспетчер команд CLI."""
    if command == "register":
        _handle_register(args)
    elif command in {"exit", "quit"}:
        print("Выход из ValutaTrade Hub.")
        raise SystemExit
    else:
        print(f"Неизвестная команда '{command}'. "
              "Попробуйте: register, login, show-portfolio, buy, sell, get-rate."
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
