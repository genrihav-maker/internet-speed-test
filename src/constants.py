"""Константы сервиса: имя приложения, путь конфига и дефолты логирования/замера."""

from pathlib import Path

APP_TITLE = "internet-speed-test"
DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.d" / "config.yml"

LOG_LEVEL = "info"
STREAM_LOG_LEVEL = "debug"
FILE_LOG_LEVEL = "info"
LOG_FILE_PATH = "logs/server.log"

DEFAULT_RUNS = 10
MAX_RUNS = 100
DEFAULT_TIMEOUT = 60
MAX_TIMEOUT = 600
