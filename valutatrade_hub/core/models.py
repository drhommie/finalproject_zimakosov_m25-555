import hashlib
from datetime import datetime
from typing import Any, Dict


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
