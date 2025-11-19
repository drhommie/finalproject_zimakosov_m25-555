from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class _Defaults:
    """Значения по умолчанию для конфигурации проекта."""

    data_dir: Path = BASE_DIR / "data"
    logs_dir: Path = BASE_DIR / "logs"
    rates_ttl_seconds: int = 300
    default_base_currency: str = "USD"
    log_level: str = "INFO"
    log_format: str = (
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )


class SettingsLoader:
    """Singleton для загрузки и кеширования конфигурации проекта.

    Источник конфигурации:
    - pyproject.toml → секция [tool.valutatrade]
    - при отсутствии ключа используется значение по умолчанию.

    Доступные ключи (минимум):
    - data_dir: путь к каталогу с JSON-файлами
    - logs_dir: путь к каталогу логов
    - rates_ttl_seconds: TTL курсов в секундах
    - default_base_currency: базовая валюта по умолчанию (например, USD)
    - log_level: уровень логирования (DEBUG/INFO/...)
    - log_format: формат строк логов
    """

    _instance: "SettingsLoader | None" = None
    _initialized: bool = False

    def __new__(cls, *args: Any, **kwargs: Any) -> "SettingsLoader":
        """Реализация паттерна Singleton через __new__.

        Такой вариант выбран за простоту и читаемость:
        - контролируем создание экземпляра в одном месте;
        - исключаем дубли при множественных импортах.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self.__class__._initialized:
            return
        self.__class__._initialized = True

        self._defaults = _Defaults()
        self._config: Dict[str, Any] = {}
        self.reload()

    def _load_from_pyproject(self) -> Dict[str, Any]:
        """Загрузка конфигурации из pyproject.toml (секция [tool.valutatrade])."""
        pyproject_path = BASE_DIR / "pyproject.toml"
        if not pyproject_path.exists():
            return {}

        with pyproject_path.open("rb") as f:
            data = tomllib.load(f)

        tool_section = data.get("tool", {})
        return tool_section.get("valutatrade", {}) or {}

    def reload(self) -> None:
        """Полная перезагрузка конфигурации из pyproject.toml."""
        raw = self._load_from_pyproject()

        cfg: Dict[str, Any] = {}

        data_dir = Path(
            raw.get("data_dir", self._defaults.data_dir),
        )
        logs_dir = Path(
            raw.get("logs_dir", self._defaults.logs_dir),
        )
        rates_ttl_seconds = int(
            raw.get("rates_ttl_seconds", self._defaults.rates_ttl_seconds),
        )
        default_base_currency = str(
            raw.get(
                "default_base_currency",
                self._defaults.default_base_currency,
            ),
        ).upper()
        log_level = str(
            raw.get("log_level", self._defaults.log_level),
        ).upper()
        log_format = str(
            raw.get("log_format", self._defaults.log_format),
        )

        cfg["data_dir"] = data_dir
        cfg["logs_dir"] = logs_dir
        cfg["rates_ttl_seconds"] = rates_ttl_seconds
        cfg["default_base_currency"] = default_base_currency
        cfg["log_level"] = log_level
        cfg["log_format"] = log_format

        cfg["users_file"] = data_dir / "users.json"
        cfg["portfolios_file"] = data_dir / "portfolios.json"
        cfg["rates_file"] = data_dir / "rates.json"

        self._config = cfg

    def get(self, key: str, default: Any | None = None) -> Any:
        """Получить значение конфигурации по ключу.

        Если ключ не найден, возвращается default.
        """
        return self._config.get(key, default)
