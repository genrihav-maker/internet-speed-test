# internet-speed-test

## Задание

Написать скрипт-замерятель скорости интернета со своего компьютера.

Он должен принимать адрес, куда стучаться (какая-нибудь тяжелая картинка),
запускать последовательно 10 запросов к этому адресу, дожидаться ответа,
вычислять среднее время запроса, объем скачанных данных и печатать в консоли
скорость мб/с.

Ответ залить на github и дать репозиторий с инструкциями.

## Реализация

Замер скорости интернета со своего компьютера.

Скрипт принимает адрес (ссылку на какой-нибудь тяжёлый файл/картинку),
последовательно выполняет N запросов к этому адресу, дожидается каждого ответа,
считает объём скачанных данных и среднее время запроса и печатает в консоль
среднюю скорость в МБ/с. Запросы выполняются через `httpx`, ответы читаются
потоково (chunk-by-chunk), поэтому он подходит и для тяжёлых файлов.

## Требования

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (менеджер пакетов)

## Установка

```bash
git clone git@github.com:genrihav-maker/internet-speed-test.git
cd internet-speed-test
uv sync
```

`uv sync` создаст `.venv` и установит зависимости из `pyproject.toml` (закреплены в `uv.lock`).

## Запуск

```bash
uv run python -m src.speed_test <URL>                       # 10 запросов (по умолчанию)
uv run python -m src.speed_test <URL> -n 20                 # 20 запросов
uv run python -m src.speed_test <URL> -n 10 -t 60           # таймаут одного запроса, сек
uv run python -m src.speed_test --help
```

Пример:

```bash
uv run python -m src.speed_test https://speed.hetzner.de/100MB.bin
```

Количество запросов по умолчанию — 10 (`measure.default_runs` из `config.d/config.yml`).

Общие флаги:

```bash
uv run python -m src.speed_test --version   # печатает версию сервиса
uv run python -m src.speed_test --name      # печатает имя сервиса
```

## Конфигурация

Настройки задаются в `config.d/config.yml` (шаблон — `config.d/config.yml_example`):

```yaml
logger:
  log_level: info
  log_format: "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
  stream:
    log_level: debug
    log_format: "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
  file:
    log_level: info
    log_format: "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    path: logs/service.log

measure:
  default_runs: 10
  max_runs: 100
  default_timeout: 60
  max_timeout: 600
```

- `logger` — настройки логирования: хендлер `stream` (консоль) и опциональный
  `file` (файл). Если секция `file` не задана — в файл ничего не пишется.
  `log_format` на верхнем уровне — формат по умолчанию, `stream.log_format` /
  `file.log_format` переопределяют его для конкретного хендлера. Файловый лог
  ротируется раз в сутки (midnight), хранится 7 последних файлов.
- `measure` — лимиты замера: количество запросов по умолчанию и максимум,
  таймаут одного запроса по умолчанию и максимум.

## Пример вывода

```
2026-09-16 09:28:21,494 | DEBUG | internet-speed-test | measure start url=http://... runs=3 timeout=60   ← debug
2026-09-16 09:28:21,536 | DEBUG | internet-speed-test | Запрос 1/3: 2.00 МБ за 0.040 с (50.00 МБ/с)     ← debug
2026-09-16 09:28:21,561 | DEBUG | internet-speed-test | Запрос 2/3: 2.00 МБ за 0.025 с (80.00 МБ/с)     ← debug
2026-09-16 09:28:23,561 | DEBUG | internet-speed-test | Запрос 3/3: 0.10 МБ за 2.000 с (0.05 МБ/с)      ← debug
2026-09-16 09:28:23,561 | INFO  | internet-speed-test | Среднее время запроса: 0.688 с, скачано: 4.10 МБ, скорость: 1.99 МБ/с
```

Итог — одной строкой: среднее время запроса, объём скачанных данных и средняя
скорость (всегда в МБ/с). Детали замера (запросы) логируются на уровне `debug`
и видны только при `log_level: debug` в конфиге.

Если ни один запрос не выполнился успешно — лог-сообщение об ошибке и код
выхода `1`; невалидные `-n`/`-t` (меньше 1) дают ошибку и код выхода `1` тоже.

## Как это работает

1. Для каждого запроса файл скачивается потоково через `httpx.stream`, время
   замеряется через `time.perf_counter` от начала запроса до получения
   последнего байта.
2. Скорость одного запроса: `размер / время`.
3. Средняя скорость: `суммарный объём / суммарное время успешных запросов`.

## Архитектура

Проект построен на модульной ООП-схеме:

- **`OneModule`** (`src/base.py`) — абстрактный базовый класс модулей.
  Модуль собирается статическим фабричным методом `build(main_module)` и
  освобождает ресурсы в `destroy()`. Класс-метод `fromtypehint()` находит
  модули по typehint-аннотациям.
- **`OneConfig`** (`src/config.py`) — читает `config.d/config.yml` и валидирует
  структуру через Pydantic; собирается первым (`build(main_module, path=...)`),
  имеет свойства `logger` и `measure`.
- **`OneLogger`** (`src/logger.py`) — настраивает логирование по данным
  `OneConfig`; второй. `destroy()` закрывает stream/file-хендлеры.
- **`MainModule`** (`src/main_module.py`) — «сервис»: модули объявляются
  class-level typehint'ами (`config`, `logger`) и собираются автоматически
  в порядке объявления в `__init__`. Реализует `modules`, `destroy_modules()`
  (через `atexit`, обратный порядок) и метод замера `measure_speed()`.
  Поддерживает передачу параметров модулям через kwargs, например
  `MainModule(config_path=...)` для тестов.
- **`src/speed_test.py`** — CLI-точка входа: парсит `url`/`-n`/`-t`
  (а также `--version`/`--name`), использует `MainModule().measure_speed()`
  и выводит результат через логгер.

## Тесты

```bash
uv run pytest
```

Тесты в `tests/` используют локальный HTTP-сервер (без внешней сети): покрывают
логику замера (`measure_speed`) и валидацию конфига (`OneConfig`).

## Линтинг и форматирование

Проект использует [ruff](https://docs.astral.sh/ruff/) (конфиг в
`[tool.ruff]`, правила E/F/I/UP/B/W):

```bash
uv run ruff check .       # lint
uv run ruff check . --fix # lint + автоисправление
uv run ruff format .      # форматирование
```

## Версионирование

Версия задана в `pyproject.toml` (`[project].version`) и дублируется в
`src/__init__.py`. Управление версиями — через `bumpver`
(правила в `[tool.bumpver]`, формула `MAJOR.MINOR.PATCH`):

```bash
uv run bumpver show                # текущая версия
uv run bumpver update --patch     # 1.2.0 -> 1.2.1
```

При обновлении bumpver сам правит версию в `pyproject.toml`, создаёт коммит
(`Bump version ...`) и git-тег (`v<версия>`). Пуш не выполняется (`push = false`),
запушьте вручную:

```bash
git push origin main --tags
```