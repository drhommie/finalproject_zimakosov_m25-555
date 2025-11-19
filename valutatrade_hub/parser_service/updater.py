from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from ..core.exceptions import ApiRequestError
from ..logging_config import get_actions_logger
from .api_clients import (
    BaseApiClient,
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from .config import ParserConfig
from .storage import (
    append_exchange_rate_entry,
    build_exchange_rate_entry,
    update_rates_snapshot_from_entries,
)


class RatesUpdater:
    """Координатор процесса обновления курсов.

    Задачи:
    - опрос всех API-клиентов;
    - объединение полученных курсов;
    - запись истории в exchange_rates.json;
    - обновление снимка в rates.json;
    - подробное логирование шагов и ошибок.
    """

    def __init__(
        self,
        clients: Iterable[BaseApiClient] | None = None,
        config: ParserConfig | None = None,
    ) -> None:
        self.config = config or ParserConfig()
        # Если явно не передали клиентов — создаём дефолтные.
        if clients is None:
            self.clients: List[BaseApiClient] = [
                CoinGeckoClient(self.config),
                ExchangeRateApiClient(self.config),
            ]
        else:
            self.clients = list(clients)

        self._logger = get_actions_logger()

    def run_update(self) -> bool:
        """Запустить один цикл обновления курсов.

        Алгоритм:
        1. Для каждого клиента вызываем fetch_rates().
        2. Собираем все пары в единый список записей журнала.
        3. Пишем каждую запись в exchange_rates.json.
        4. Обновляем снимок курсов в rates.json.
        5. Логируем успехи и ошибки.

        Возвращает:
            True, если были получены и сохранены хоть какие-то данные,
            False — если ни один клиент не дал валидных курсов.
        """
        logger = self._logger
        started_at = datetime.now(timezone.utc)
        started_str = started_at.isoformat().replace("+00:00", "Z")

        client_names = [c.__class__.__name__ for c in self.clients]
        logger.info(
            "PARSER_UPDATE start timestamp=%s clients=%s",
            started_str,
            client_names,
        )

        all_entries: List[Dict[str, Any]] = []

        for client in self.clients:
            client_name = client.__class__.__name__
            logger.info(
                "PARSER_UPDATE client=%s status=START",
                client_name,
            )

            try:
                rates = client.fetch_rates()
            except ApiRequestError as exc:
                logger.error(
                    "PARSER_UPDATE client=%s status=ERROR error=%s",
                    client_name,
                    exc,
                )
                # Продолжаем работать с другими клиентами.
                continue
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "PARSER_UPDATE client=%s status=UNEXPECTED_ERROR error=%s",
                    client_name,
                    exc,
                )
                continue

            if not rates:
                logger.warning(
                    "PARSER_UPDATE client=%s status=NO_DATA",
                    client_name,
                )
                continue

            logger.info(
                "PARSER_UPDATE client=%s status=OK pairs=%s",
                client_name,
                ", ".join(sorted(rates.keys())),
            )

            for pair_key, rate in rates.items():
                try:
                    from_code, to_code = pair_key.split("_", 1)
                except ValueError:
                    logger.error(
                        "PARSER_UPDATE client=%s status=SKIP_INVALID_PAIR "
                        "pair=%s",
                        client_name,
                        pair_key,
                    )
                    continue

                try:
                    entry = build_exchange_rate_entry(
                        from_currency=from_code,
                        to_currency=to_code,
                        rate=rate,
                        source=client_name,
                        timestamp=started_at,
                        meta={"client": client_name},
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "PARSER_UPDATE client=%s status=SKIP_INVALID_ENTRY "
                        "pair=%s error=%s",
                        client_name,
                        pair_key,
                        exc,
                    )
                    continue

                append_exchange_rate_entry(entry)
                all_entries.append(entry)

        if not all_entries:
            logger.warning(
                "PARSER_UPDATE completed: no entries collected; "
                "rates.json not updated.",
            )
            return False

        update_rates_snapshot_from_entries(all_entries)
        logger.info(
            "PARSER_UPDATE completed successfully entries=%d",
            len(all_entries),
        )
        return True
