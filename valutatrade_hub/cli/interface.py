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
    get_rate,
    get_user_portfolio_summary,
    login_user,
    register_user,
    sell_currency,
)
from ..core.utils import validate_currency_code
from ..parser_service.api_clients import (
    BaseApiClient,
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from ..parser_service.config import ParserConfig
from ..parser_service.storage import load_rates_snapshot
from ..parser_service.updater import RatesUpdater

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


def _parse_update_rates_args(args: list[str]) -> str | None:
    """Разобрать аргументы команды update-rates.

    Поддерживается флаг:
    --source <coingecko|exchangerate>
    """
    source: str | None = None
    idx = 0

    while idx < len(args):
        token = args[idx]
        if token == "--source":
            if idx + 1 >= len(args):
                raise ValueError(
                    "Флаг --source требует значения: "
                    "coingecko или exchangerate.",
                )
            if source is not None:
                raise ValueError(
                    "Параметр --source нельзя указывать несколько раз.",
                )
            value = args[idx + 1].lower()
            if value not in ("coingecko", "exchangerate"):
                raise ValueError(
                    "Недопустимое значение для --source. "
                    "Допустимы: coingecko, exchangerate.",
                )
            source = value
            idx += 2
        else:
            raise ValueError(
                f"Неизвестный аргумент для update-rates: {token}",
            )

    return source


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


def _parse_show_rates_args(
    args: list[str],
) -> tuple[str | None, int | None, str | None]:
    """Разобрать аргументы команды show-rates.

    Поддерживаются флаги:
    --currency <CODE>
    --top <N>
    --base <CODE>
    Нельзя одновременно использовать --currency и --top.
    """
    currency: str | None = None
    top_n: int | None = None
    base: str | None = None

    idx = 0
    while idx < len(args):
        token = args[idx]
        if token == "--currency":
            if idx + 1 >= len(args):
                raise ValueError(
                    "Флаг --currency требует значения: код валюты.",
                )
            if currency is not None:
                raise ValueError(
                    "Параметр --currency нельзя указывать несколько раз.",
                )
            currency = validate_currency_code(args[idx + 1])
            idx += 2
        elif token == "--top":
            if idx + 1 >= len(args):
                raise ValueError(
                    "Флаг --top требует значения: положительное целое число.",
                )
            if top_n is not None:
                raise ValueError(
                    "Параметр --top нельзя указывать несколько раз.",
                )
            try:
                value = int(args[idx + 1])
            except ValueError as exc:
                raise ValueError(
                    "Значение --top должно быть целым числом.",
                ) from exc
            if value <= 0:
                raise ValueError(
                    "Значение --top должно быть положительным.",
                )
            top_n = value
            idx += 2
        elif token == "--base":
            if idx + 1 >= len(args):
                raise ValueError(
                    "Флаг --base требует значения: код валюты.",
                )
            if base is not None:
                raise ValueError(
                    "Параметр --base нельзя указывать несколько раз.",
                )
            base = validate_currency_code(args[idx + 1])
            idx += 2
        else:
            raise ValueError(
                f"Неизвестный аргумент для show-rates: {token}",
            )

    if currency is not None and top_n is not None:
        raise ValueError(
            "Нельзя одновременно использовать --currency и --top.",
        )

    return currency, top_n, base


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
        )

        code = result["currency_code"]
        value = float(result["amount"])
        base = result["base_currency"]
        rate = float(result["rate"])
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
        )

        code = result["currency_code"]
        value = float(result["amount"])
        base = result["base_currency"]
        old_balance = float(result["old_balance"])
        new_balance = float(result["new_balance"])
        rate = float(result["rate"])
        estimated_value = float(result["estimated_value"])

        amount_str = f"{value:.4f}"
        old_str = f"{old_balance:.4f}"
        new_str = f"{new_balance:.4f}"
        rate_str = f"{rate:,.2f}"
        estimated_str = f"{estimated_value:,.2f}"

        print(
            f"Продажа выполнена: {amount_str} {code} по курсу "
            f"{rate_str} {base}/{code}",
        )
        print("Изменения в портфеле:")
        print(f"- {code}: было {old_str} → стало {new_str}")
        print(f"Оценочная выручка: {estimated_str} {base}")
    except InsufficientFundsError as exc:
        print(str(exc))
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
        print(str(exc))


def _handle_update_rates(args: list[str]) -> None:
    """Обработчик команды update-rates."""
    try:
        source = _parse_update_rates_args(args)
    except ValueError as exc:
        print(str(exc))
        return

    print("Запуск обновления курсов...")

    config = ParserConfig()
    clients: list[BaseApiClient]

    if source == "coingecko":
        print("Источник: только CoinGecko.")
        clients = [CoinGeckoClient(config)]
    elif source == "exchangerate":
        print("Источник: только ExchangeRate-API.")
        clients = [ExchangeRateApiClient(config)]
    else:
        print("Источники: CoinGecko и ExchangeRate-API.")
        clients = []

    try:
        if clients:
            updater = RatesUpdater(clients=clients, config=config)
        else:
            updater = RatesUpdater(config=config)

        success = updater.run_update()
    except ApiRequestError as exc:
        print(f"Ошибка при обновлении курсов: {exc}")
        print("Подробности смотрите в logs/actions.log.")
        return

    snapshot = load_rates_snapshot()
    pairs = snapshot.get("pairs") or {}
    last_refresh = snapshot.get("last_refresh") or "неизвестно"

    total_rates = len(pairs)

    if not success:
        print("Обновление завершено с ошибками.")
        if total_rates:
            print(
                "Текущие доступные курсы: "
                f"{total_rates}. Последнее обновление: {last_refresh}.",
            )
        print("Подробности смотрите в logs/actions.log.")
        return

    if not total_rates:
        print(
            "Обновление завершено, но курсы не найдены. "
            "Проверьте логи в logs/actions.log.",
        )
        return

    print(
        "Обновление успешно. "
        f"Всего обновлено курсов: {total_rates}. "
        f"Последнее обновление: {last_refresh}.",
    )


def _handle_get_rate(args: List[str]) -> None:
    """Обработчик команды get-rate."""
    try:
        from_code, to_code = _parse_get_rate_args(args)
        rate, updated_at = get_rate(from_code, to_code)

        base = from_code.strip().upper()
        quote = to_code.strip().upper()
        updated_str = updated_at.strftime("%Y-%m-%d %H:%M:%S")

        if rate != 0:
            reverse_rate = 1.0 / rate
        else:
            reverse_rate = 0.0

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
        print(str(exc))


def _handle_show_rates(args: list[str]) -> None:
    """Обработчик команды show-rates."""
    try:
        currency, top_n, base = _parse_show_rates_args(args)
    except ValueError as exc:
        print(str(exc))
        return

    snapshot = load_rates_snapshot()
    pairs = snapshot.get("pairs") or {}
    if not isinstance(pairs, dict) or not pairs:
        print(
            "Локальный кеш курсов пуст. "
            "Выполните 'update-rates', чтобы загрузить данные.",
        )
        return

    last_refresh = snapshot.get("last_refresh") or "неизвестно"

    config = ParserConfig()
    target_base = (base or config.BASE_FIAT_CURRENCY).upper()

    # Определяем базовую валюту, относительно которой хранятся пары.
    snapshot_base: str | None = None
    for key in pairs:
        if "_" in key:
            _, base_code = key.split("_", 1)
            snapshot_base = base_code.upper()
            break

    if snapshot_base is None:
        print(
            "Формат файла кеша некорректен. "
            "Перезапустите 'update-rates'.",
        )
        return

    # Подготавливаем список (from_code, rate_in_target_base, pair_key_for_output).
    items: list[tuple[str, float, str]] = []

    if target_base == snapshot_base:
        # Базовая валюта совпадает с хранящейся — берём значения как есть.
        for pair_key, entry in pairs.items():
            if not isinstance(entry, dict):
                continue
            rate = entry.get("rate")
            if not isinstance(rate, (int, float)):
                continue
            try:
                from_code, to_code = pair_key.split("_", 1)
            except ValueError:
                continue
            items.append((from_code, float(rate), f"{from_code}_{to_code}"))
    else:
        # Нужна переконвертация в target_base, если есть курс target_base→snapshot_base.
        base_pair_key = f"{target_base}_{snapshot_base}"
        base_entry = pairs.get(base_pair_key)
        if not isinstance(base_entry, dict) or not isinstance(
            base_entry.get("rate"),
            (int, float),
        ):
            print(
                "Не удалось конвертировать в базовую валюту "
                f"'{target_base}': нет курса {target_base}_{snapshot_base}.",
            )
            return

        base_rate = float(base_entry["rate"])  # 1 target_base = base_rate snapshot_base

        for pair_key, entry in pairs.items():
            if not isinstance(entry, dict):
                continue
            rate = entry.get("rate")
            if not isinstance(rate, (int, float)):
                continue
            try:
                from_code, to_code = pair_key.split("_", 1)
            except ValueError:
                continue
            if to_code.upper() != snapshot_base:
                continue
            # 1 from_code = rate * snapshot_base
            # 1 target_base = base_rate * snapshot_base
            # => 1 from_code = (rate / base_rate) * target_base
            converted = float(rate) / base_rate
            items.append(
                (from_code, converted, f"{from_code}_{target_base}"),
            )

    if not items:
        print(
            "Локальный кеш курсов не содержит ни одной корректной записи. "
            "Выполните 'update-rates'.",
        )
        return

    # Фильтр по --currency.
    if currency is not None:
        currency_upper = currency.upper()
        filtered = [item for item in items if item[0] == currency_upper]
        if not filtered:
            print(
                f"Курс для '{currency_upper}' не найден в кеше.",
            )
            return
        items = filtered

    # Фильтр по --top: только криптовалюты.
    if top_n is not None:
        crypto_set = set(config.CRYPTO_CURRENCIES)
        crypto_items = [item for item in items if item[0] in crypto_set]
        if not crypto_items:
            print(
                "В кеше нет данных по криптовалютам для вычисления --top.",
            )
            return
        # Сортируем по убыванию курса.
        crypto_items.sort(key=lambda x: x[1], reverse=True)
        items = crypto_items[:top_n]
    else:
        # Без --top сортируем по алфавиту ключа пары.
        items.sort(key=lambda x: x[2])

    print(f"Rates from cache (updated at {last_refresh}):")
    for _, rate, pair_key in items:
        print(f"- {pair_key}: {rate:.5f}")


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
    elif command == "update-rates":
        _handle_update_rates(args)
    elif command == "show-rates":
        _handle_show_rates(args)        
    elif command in {"exit", "quit"}:
        print("Выход из ValutaTrade Hub.")
        raise SystemExit
    else:
        print(
            "Неизвестная команда "
            f"'{command}'. Попробуйте: register, login, show-portfolio, "
            "buy, sell, get-rate, update-rates, show-rates.",
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


