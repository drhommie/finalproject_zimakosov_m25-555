from __future__ import annotations

"""Parser Service: обновление курсов валют из внешних API.

Состоит из:
- config: конфигурация API и параметров обновления
- api_clients: работа с внешними API
- storage: операции чтения/записи exchange_rates.json
- updater: основной модуль обновления курсов
- scheduler: планировщик периодического обновления
"""
