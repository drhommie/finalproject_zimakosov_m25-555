from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Dict, Optional


class User:
    """Модель пользователя системы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        # используем свойства, чтобы сработали проверки
        self.user_id = user_id
        self.username = username
        self.salt = salt
        self._hashed_password = hashed_password
        self.registration_date = registration_date

    # ---------- Свойства ----------

    @property
    def user_id(self) -> int:
        return self._user_id

    @user_id.setter
    def user_id(self, value: int) -> None:
        if value <= 0:
            raise ValueError("user_id должен быть положительным целым числом.")
        self._user_id = value

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым.")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

# Сеттер для hashed_password не предоставляется.
# Пароль меняется только через change_password().

    @property
    def salt(self) -> str:
        return self._salt

    @salt.setter
    def salt(self, value: str) -> None:
        if not value:
            raise ValueError("Соль не может быть пустой.")
        self._salt = value

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    @registration_date.setter
    def registration_date(self, value: datetime) -> None:
        if not isinstance(value, datetime):
            raise TypeError("registration_date должен быть datetime.")
        self._registration_date = value

    # ---------- Вспомогательные методы ----------

    def _hash_password(self, password: str) -> str:
        """Выполнить одностороннее хеширование пароля с использованием соли."""
        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов.")
        data = f"{password}{self._salt}".encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    # ---------- Публичные методы ----------

    def get_user_info(self) -> Dict[str, Any]:
        """Вернуть информацию о пользователе без пароля."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Изменить пароль пользователя (с хешированием)."""
        self._hashed_password = self._hash_password(new_password)

    def verify_password(self, password: str) -> bool:
        """Проверка введённого пароля на совпадение с сохранённым хешем."""
        try:
            return self._hashed_password == self._hash_password(password)
        except ValueError:
            # если пароль меньше 4 символов, сразу False
            return False

class Wallet:
    """Кошелёк пользователя для одной конкретной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        self.currency_code = currency_code
        self.balance = balance  # через setter, чтобы прошла проверка

    # ----------- Свойства -----------

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом.")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным.")
        self._balance = float(value)

    # ----------- Методы -----------

    def deposit(self, amount: float) -> None:
        """Пополнение баланса."""
        if not isinstance(amount, (int, float)):
            raise TypeError("Сумма пополнения должна быть числом.")
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной.")
        self._balance += float(amount)

    def withdraw(self, amount: float) -> None:
        """Снятие средств при достаточном балансе."""
        if not isinstance(amount, (int, float)):
            raise TypeError("Сумма снятия должна быть числом.")
        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительной.")
        if amount > self._balance:
            raise ValueError("Недостаточно средств для снятия.")
        self._balance -= float(amount)

    def get_balance_info(self) -> dict:
        """Информация о текущем балансе кошелька."""
        return {
            "currency_code": self.currency_code,
            "balance": self._balance,
        }

class Portfolio:
    """Портфель всех кошельков одного пользователя."""

    def __init__(
        self,
        user: User,
        wallets: Optional[Dict[str, Wallet]] = None,
    ) -> None:
        self._user = user
        self._user_id = user.user_id
        self._wallets: Dict[str, Wallet] = wallets or {}

    # ----------- Свойства -----------

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def user(self) -> User:
        """Объект пользователя, только для чтения."""
        return self._user

    @property
    def wallets(self) -> Dict[str, Wallet]:
        """Копия словаря кошельков."""
        return dict(self._wallets)

    # ----------- Методы -----------

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавить новый кошелёк для указанной валюты."""
        code = currency_code.upper()
        if code in self._wallets:
            raise ValueError(f"Кошелёк для валюты {code} уже существует.")
        wallet = Wallet(currency_code=code)
        self._wallets[code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet:
        """Получить кошелёк по коду валюты."""
        code = currency_code.upper()
        try:
            return self._wallets[code]
        except KeyError as exc:
            raise KeyError(f"Кошелёк для валюты {code} не найден.") from exc

    def get_total_value(self, base_currency: str = "USD") -> float:
        """Общая стоимость портфеля в базовой валюте.

        Для упрощения используются фиксированные условные курсы.
        """
        exchange_rates: Dict[str, Dict[str, float]] = {
            "USD": {"USD": 1.0, "EUR": 0.9, "BTC": 0.00002},
            "EUR": {"USD": 1.1, "EUR": 1.0, "BTC": 0.000022},
            "BTC": {"USD": 50000.0, "EUR": 45000.0, "BTC": 1.0},
        }

        base = base_currency.upper()
        total = 0.0

        for code, wallet in self._wallets.items():
            cur = code.upper()
            if cur == base:
                rate = 1.0
            else:
                try:
                    rate = exchange_rates[cur][base]
                except KeyError as exc:
                    raise ValueError(
                        f"Нет курса для пары {cur}/{base}."
                    ) from exc
            total += wallet.balance * rate

        return total
