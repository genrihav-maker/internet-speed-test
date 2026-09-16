#!/usr/bin/env python3
"""CLI-замер скорости интернета: python -m src.speed_test <URL>."""

import argparse
import sys

from . import __version__
from .main_module import MainModule


def main() -> None:
    """Запускает замер скорости из командной строки.

    Поддерживает флаги --version/--name (печать метаданных и выход),
    -n/--runs (количество запросов) и -t/--timeout (таймаут запроса, сек).
    Значения по умолчанию берутся из config.d/config.yml (measure).

    Raises:
        SystemExit: при ошибке использования, невалидных параметрах или
            полном провале замера (код выхода 1).
    """
    parser = argparse.ArgumentParser(
        description="Замер скорости интернета: N последовательных запросов к адресу."
    )
    parser.add_argument("url", nargs="?", help="Адрес файла/картинки для скачивания")
    parser.add_argument("-n", "--runs", type=int, default=None, help="Количество запросов")
    parser.add_argument(
        "-t", "--timeout", type=int, default=None, help="Таймаут одного запроса, сек"
    )
    parser.add_argument(
        "--version", "-v", action="store_true", help="print service version and exit"
    )
    parser.add_argument(
        "--name", "--title", action="store_true", help="print service name and exit"
    )
    args = parser.parse_args()

    if args.version:
        print(__version__, end="", flush=True)
        sys.exit(0)

    if args.name:
        print(MainModule.title, end="", flush=True)
        sys.exit(0)

    if args.url is None:
        parser.error("не указан url")

    mm = MainModule()
    log = mm.logger

    settings = mm.config.measure
    runs = args.runs if args.runs else settings.default_runs
    timeout = args.timeout if args.timeout else settings.default_timeout
    if runs <= 0 or timeout <= 0:
        log.error("Ошибка: runs и timeout должны быть больше нуля.")
        sys.exit(1)

    result = mm.measure_speed(args.url, runs, timeout)

    for i, r in enumerate(result["per_request"], start=1):
        if r["error"] is not None:
            log.warning("Запрос %d/%d: ОШИБКА — %s", i, result["runs"], r["error"])
        else:
            log.info(
                "Запрос %d/%d: %.2f МБ за %.3f с (%.2f МБ/с)",
                i,
                result["runs"],
                r["size_bytes"] / 1024 / 1024,
                r["elapsed_s"],
                r["speed_mb_s"],
            )

    if result["runs_ok"] == 0:
        log.error("Ошибка: ни один запрос не выполнился успешно.")
        sys.exit(1)

    log.info("Всего скачано: %.2f МБ", result["total_bytes"] / 1024 / 1024)
    log.info("Среднее время запроса: %.3f с", result["avg_time_s"])
    log.info("Средняя скорость: %.2f МБ/с", result["avg_speed_mb_s"])


if __name__ == "__main__":
    main()
