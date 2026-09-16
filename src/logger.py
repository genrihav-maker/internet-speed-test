"""OneLogger: конфигурация логирования по данным OneConfig."""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING

from .base import OneModule
from .config import OneConfig
from .constants import (
    APP_TITLE,
    LOG_BACKUP_COUNT,
    LOG_ROTATE_WHEN,
)

if TYPE_CHECKING:
    from .main_module import MainModule


def _to_level(level: str, default: int = logging.INFO) -> int:
    """Переводит строковый уровень логирования в константу logging.

    Args:
        level: строковый уровень (например, "info" или "WARN").
        default: уровень по умолчанию, если строка не распознана.

    Returns:
        Одна из констант logging.DEBUG/INFO/WARNING/ERROR.
    """
    level = (level or "").upper()
    if level == "WARN":
        return logging.WARNING
    return getattr(logging, level, default)


def get_logger(name: str) -> logging.Logger:
    """Возвращает логгер по имени, попадающий в корневые хендлеры.

    Args:
        name: имя логгера.

    Returns:
        Экземпляр logging.Logger.
    """
    return logging.getLogger(name)


class OneLogger(OneModule):
    """Модуль логирования: настраивает корневого логгера (stream + file).

    Собирается вторым, после OneConfig.
    """

    def __init__(self, config: OneConfig) -> None:
        """Инициализирует модуль.

        Args:
            config: OneConfig с настройками логирования.
        """
        super().__init__("logger")
        self.config = config
        self.logger: logging.Logger | None = None
        self._handlers: list[logging.Handler] = []

    @classmethod
    def build(cls, main_module: "MainModule") -> "OneLogger":
        """Собирает и настраивает логгеры из настроек конфига.

        Args:
            main_module: MainModule с уже собранным модулем config.

        Returns:
            Собранный OneLogger.
        """
        self = cls(main_module.config)
        settings = self.config.logger
        default_format = settings.log_format

        root = logging.getLogger()
        root.setLevel(_to_level(settings.log_level, logging.INFO))
        for handler in list(root.handlers):
            root.removeHandler(handler)
            handler.close()

        stream = None
        if settings.stream is not None:
            stream = logging.StreamHandler(sys.stdout)
            stream.setLevel(_to_level(settings.stream.log_level, logging.DEBUG))
            stream.setFormatter(logging.Formatter(settings.stream.log_format or default_format))
            root.addHandler(stream)
            self._handlers.append(stream)

        file_handler = None
        if settings.file is not None:
            log_path = Path(settings.file.path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = TimedRotatingFileHandler(
                log_path,
                when=LOG_ROTATE_WHEN,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
                delay=True,
            )
            file_handler.setLevel(_to_level(settings.file.log_level, logging.INFO))
            file_handler.setFormatter(logging.Formatter(settings.file.log_format or default_format))
            root.addHandler(file_handler)
            self._handlers.append(file_handler)

        self.logger = logging.getLogger(APP_TITLE)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        self.info(
            "OneLogger ready: root=%s stream=%s file=%s",
            root.getEffectiveLevel(),
            stream.level if stream is not None else "disabled",
            file_handler.baseFilename if file_handler else "disabled",
        )
        return self

    def destroy(self) -> None:
        """Закрывает stream/file хендлеры перед завершением программы."""
        for handler in self._handlers:
            handler.close()
        self._handlers.clear()

    def debug(self, msg: str, *args: object) -> None:
        """Логирует отладочное сообщение.

        Args:
            msg: шаблон сообщения.
            *args: аргументы форматирования.
        """
        if self.logger:
            self.logger.debug(msg, *args)

    def info(self, msg: str, *args: object) -> None:
        """Логирует информационное сообщение.

        Args:
            msg: шаблон сообщения.
            *args: аргументы форматирования.
        """
        if self.logger:
            self.logger.info(msg, *args)

    def warning(self, msg: str, *args: object) -> None:
        """Логирует предупреждение.

        Args:
            msg: шаблон сообщения.
            *args: аргументы форматирования.
        """
        if self.logger:
            self.logger.warning(msg, *args)

    def error(self, msg: str, *args: object) -> None:
        """Логирует ошибку.

        Args:
            msg: шаблон сообщения.
            *args: аргументы форматирования.
        """
        if self.logger:
            self.logger.error(msg, *args)
