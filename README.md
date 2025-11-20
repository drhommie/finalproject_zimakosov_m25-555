# ValutaTrade Hub

Итоговый консольный проект: платформа для отслеживания и симуляции торговли валютами (фиат + крипта).

Проект оформлен как Python-пакет `valutatrade_hub` и запускается через CLI.  
Пользователь может:

- регистрироваться и входить в систему;
- управлять виртуальными кошельками (портфелем);
- покупать и продавать валюту;
- смотреть актуальные курсы;
- обновлять курсы через отдельный Parser Service.

---

## 1. Архитектура проекта

Структура каталогов:

```text
finalproject_zimakosov_m25-555/
├── data/
│   ├── users.json
│   ├── portfolios.json
│   ├── rates.json
│   └── exchange_rates.json
├── logs/
│   └── actions.log
├── valutatrade_hub/
│   ├── cli/
│   ├── core/
│   ├── infra/
│   ├── parser_service/
│   ├── decorators.py
│   └── logging_config.py
├── main.py
├── pyproject.toml
├── Makefile
└── README.md
```

---

## 2. Используемые технологии

- Python 3.12  
- Poetry  
- Ruff  
- prettytable  
- logging + rotation  
- JSON-файлы как хранилище  

---

## 3. Установка и запуск

### 3.1. Требования
- Python 3.12  
- Poetry  

```bash
git clone git@github.com:drhommie/finalproject_zimakosov_m25-555.git
cd finalproject_zimakosov_m25-555
```

### 3.2. Установка зависимостей

```bash
make install
```

или:

```bash
poetry install
```

### 3.3. Запуск CLI

```bash
poetry run project
```

или:

```bash
make project
```

---

## 4. Основные команды CLI

### 4.1. Регистрация и логин

```text
> register --username alice --password 1234
> login --username alice --password 1234
```

---

### 4.2. show-portfolio

```text
> show-portfolio
Портфель пользователя 'alice' ...
```

---

### 4.3. buy

```text
> buy --currency BTC --amount 0.05
Покупка выполнена...
```

---

### 4.4. sell

```text
> sell --currency BTC --amount 0.01
Продажа выполнена...
```

---

### 4.5. get-rate

```text
> get-rate --from USD --to BTC
Курс USD→BTC ...
```

Ошибки:
- неизвестная валюта  
- устаревший кэш  
- отсутствует курс  

---

### 4.6. update-rates (Parser Service)

```text
> update-rates
Запуск обновления курсов...
```

Поддерживаются:

```text
--source coingecko
--source exchangerate
```

---

### 4.7. show-rates

```text
> show-rates
> show-rates --currency BTC
> show-rates --top 2
```

---

## 5. Кэш курсов и TTL

Core использует:

- `data/rates.json` — актуальные данные  
- TTL задаётся в `SettingsLoader`  
- При устаревании: сообщение и предложение выполнить `update-rates`

Структура `rates.json`:

```json
{
  "pairs": {
    "BTC_USD": {
      "rate": 59337.21,
      "updated_at": "2025-11-10T12:00:00Z",
      "source": "CoinGecko"
    }
  },
  "last_refresh": "2025-11-10T12:00:01Z"
}
```

---

## 6. Журнал курсов (exchange_rates.json)

Parser Service ведёт историю всех замеров:

```json
{
  "id": "BTC_USD_2025-11-10T12:00:00Z",
  "from_currency": "BTC",
  "to_currency": "USD",
  "rate": 59337.21,
  "timestamp": "2025-11-10T12:00:00Z",
  "source": "CoinGecko",
  "meta": {
    "raw_id": "bitcoin",
    "request_ms": 124,
    "status_code": 200
  }
}
```

---

## 7. Настройка EXCHANGERATE_API_KEY

```bash
export EXCHANGERATE_API_KEY="ВАШ_КЛЮЧ"
```

ParserConfig автоматически подтягивает ключ из окружения.

---

## 8. Логирование

Все операции пишутся в `logs/actions.log`.

Пример:

```text
2025-11-19T21:48:20 [INFO] valutatrade.actions - BUY user='alice' currency='BTC' amount=0.0500 ...
```

Ошибки:

```text
error_type='InsufficientFundsError'
error_message='Недостаточно средств...'
```

---

## 9. Makefile команды

```bash
make install
make project
make lint
make build
make package-install
```

---

## 10. Демонстрация

Полный сценарий:

```text
> register --username alice --password 1234
> login --username alice --password 1234
> update-rates
> buy --currency BTC --amount 0.05
> sell --currency BTC --amount 0.01
> show-portfolio
> show-rates --top 3
> get-rate --from USD --to BTC
> exit
```

Проект демонстрирует:

- Core Service  
- Parser Service  
- JSON-хранилище  
- Singleton  
- Исключения  
- Логирование  