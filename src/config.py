"""OneConfig: чтение и валидация config.d/config.yml через Pydantic."""

from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
)

import yaml
from pydantic import BaseModel, Field

from .base import OneModule
from .constants import (
    CONFIG_PATH,
    DEFAULT_LOG_FORMAT,
    DEFAULT_RUNS,
    DEFAULT_TIMEOUT,
    FILE_LOG_LEVEL,
    LOG_FILE_PATH,
    LOG_LEVEL,
    MAX_RUNS,
    MAX_TIMEOUT,
    STREAM_LOG_LEVEL,
)

if TYPE_CHECKING:
    from .main_module import MainModule


class StreamLogSettings(BaseModel):
    """Настройки stream-хендлера логирования."""

    log_level: str = STREAM_LOG_LEVEL
    log_format: str = DEFAULT_LOG_FORMAT


class FileLogSettings(BaseModel):
    """Настройки file-хендлера логирования."""

    log_level: str = FILE_LOG_LEVEL
    log_format: str = DEFAULT_LOG_FORMAT
    path: str = LOG_FILE_PATH


class LoggerSettings(BaseModel):
    """Настройки логирования: уровень, формат, stream/file хендлеры.

    Если file не задан, записи в файл не ведутся.
    """

    log_level: str = LOG_LEVEL
    log_format: str = DEFAULT_LOG_FORMAT
    stream: StreamLogSettings = Field(default_factory=StreamLogSettings)
    file: FileLogSettings | None = None


class MeasureSettings(BaseModel):
    """Лимиты замера скорости: количество запросов и таймауты."""

    default_runs: int = Field(default=DEFAULT_RUNS, ge=1)
    max_runs: int = Field(default=MAX_RUNS, ge=1)
    default_timeout: int = Field(default=DEFAULT_TIMEOUT, ge=1)
    max_timeout: int = Field(default=MAX_TIMEOUT, ge=1)


class AppConfig(BaseModel):
    """Корневая схема config.yml: секции logger и measure."""

    logger: LoggerSettings = Field(default_factory=LoggerSettings)
    measure: MeasureSettings = Field(default_factory=MeasureSettings)


class OneConfig(OneModule):
    """Модуль конфига: читает config.d/config.yml и валидирует его.

    Собирается первым, остальные модули берут настройки из него.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        """Инициализирует модуль.

        Args:
            path: путь до config.yml; по умолчанию config.d/config.yml.
        """
        super().__init__("config")
        self.path = Path(path) if path is not None else CONFIG_PATH
        self._config: AppConfig | None = None

    @property
    def app_config(self) -> AppConfig:
        """Возвращает валидированный конфиг.

        Returns:
            AppConfig после инициализации.

        Raises:
            RuntimeError: если build() ещё не вызывался.
        """
        if self._config is None:
            raise RuntimeError("OneConfig не инициализирован: вызовите build()")
        return self._config

    @property
    def logger(self) -> LoggerSettings:
        """Возвращает настройки логирования.

        Returns:
            LoggerSettings из app_config.
        """
        return self.app_config.logger

    @property
    def measure(self) -> MeasureSettings:
        """Возвращает лимиты замера скорости.

        Returns:
            MeasureSettings из app_config.
        """
        return self.app_config.measure

    @classmethod
    def build(
        cls,
        main_module: Optional["MainModule"] = None,
        path: str | Path | None = None,
    ) -> "OneConfig":
        """Собирает OneConfig из YAML-файла.

        Args:
            main_module: MainModule, которому принадлежит модуль (часть
                контракта модуля; напрямую не используется).
            path: путь до config.yml; по умолчанию config.d/config.yml.

        Returns:
            Собранный OneConfig.

        Raises:
            pydantic.ValidationError: если структура файла не соответствует схеме.
            yaml.YAMLError: если файл не является валидным YAML.
        """
        config = cls(path)
        config._config = AppConfig.model_validate(config._load_yaml())
        return config

    def _load_yaml(self) -> dict[str, Any]:
        """Читает YAML-файл конфига.

        Returns:
            Словарь с данными конфига; {} если файл отсутствует.

        Raises:
            yaml.YAMLError: если содержимое файла — невалидный YAML.
        """
        if not self.path.exists():
            return {}
        with open(self.path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data or {}
