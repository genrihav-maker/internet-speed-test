"""MainModule: супер-класс, владеющий модулями и логикой замера скорости."""

import atexit
import time
from pathlib import Path
from typing import Any, TypedDict

import httpx

from . import __version__
from .base import OneModule
from .config import OneConfig
from .constants import APP_TITLE
from .exceptions import RequestError
from .logger import OneLogger


class PerRequestResult(TypedDict):
    """Результат одного запроса замера."""

    size_bytes: int
    elapsed_s: float
    speed_mb_s: float
    error: str | None


class MeasureResult(TypedDict):
    """Итоговый результат замера скорости."""

    url: str
    runs: int
    runs_ok: int
    total_bytes: int
    avg_time_s: float
    avg_speed_mb_s: float
    per_request: list[PerRequestResult]


class MainModule:
    """Объединяет модули системы и измеряет скорость интернета.

    Модули объявляются class-level typehint'ами (config, logger) и собираются
    автоматически в порядке объявления аннотаций: config -> logger.
    Запуск скрипта: python -m src.speed_test <URL>.
    """

    title: str = APP_TITLE
    version: str = __version__

    config: OneConfig
    logger: OneLogger

    def __init__(
        self,
        config_path: str | Path | None = None,
        **kwargs: Any,
    ) -> None:
        """Собирает модули из typehint-аннотаций класса.

        Args:
            config_path: путь до config.yml (передаётся в OneConfig).
            **kwargs: параметры модулей, сгруппированные по их именам.
        """
        if config_path is not None:
            kwargs.setdefault("config", {"path": config_path})

        self.kwargs: dict[str, Any] = kwargs
        self.startup_time: float = time.time()

        for key, module_cls in OneModule.fromtypehint(self.__class__).items():
            module_kw = kwargs.get(key, {})
            setattr(self, key, module_cls.build(self, **module_kw))

        atexit.register(self.destroy_modules)

    @property
    def modules(self) -> list[tuple[str, OneModule]]:
        """Возвращает все собранные модули.

        Returns:
            Список пар (имя модуля, экземпляр модуля).
        """
        return [
            (key, module) for key, module in vars(self).items() if isinstance(module, OneModule)
        ]

    def destroy_modules(self) -> None:
        """Освобождает ресурсы модулей в обратном порядке.

        Обратный порядок нужен, чтобы config/logger освобождались последними:
        от их работы зависят остальные модули. Вызывается через atexit.
        """
        for _, module in reversed(self.modules):
            module.destroy()

    def _download_once(self, url: str, timeout: int) -> tuple[int, float]:
        """Скачивает файл потоково и замеряет время запроса.

        Args:
            url: адрес файла/картинки для скачивания.
            timeout: таймаут одного запроса, секунд.

        Returns:
            Кортеж (размер в байтах, время в секундах).

        Raises:
            RequestError: при сетевой ошибке, таймауте или HTTP-статусе.
        """
        start = time.perf_counter()
        try:
            with httpx.stream("GET", url, timeout=timeout) as response:
                response.raise_for_status()
                size = 0
                for _chunk in response.iter_bytes():
                    size += len(_chunk)
        except httpx.HTTPError as exc:
            raise RequestError(str(exc)) from exc
        elapsed = time.perf_counter() - start
        return size, elapsed

    def _failed_result(self, exc: Exception) -> PerRequestResult:
        """Формирует результат неудачного запроса.

        Args:
            exc: исключение, из-за которого запрос не удался.

        Returns:
            Словарь результата с нулевыми метриками и текстом ошибки.
        """
        return {"size_bytes": 0, "elapsed_s": 0.0, "speed_mb_s": 0.0, "error": str(exc)}

    def measure_speed(self, url: str, runs: int = 10, timeout: int = 60) -> MeasureResult:
        """Последовательно выполняет runs запросов и собирает результат.

        Неудачные запросы не прерывают замер: их результат помечается ошибкой
        в per_request, но не учитывается в среднем времени и объёме.

        Args:
            url: адрес файла/картинки для скачивания.
            runs: количество последовательных запросов.
            timeout: таймаут одного запроса, секунд.

        Returns:
            Словарь с ключами url, runs, runs_ok, total_bytes, avg_time_s,
            avg_speed_mb_s и per_request (детали по каждому запросу).
        """
        results: list[PerRequestResult] = []
        total_bytes = 0

        self.logger.debug("measure start url=%s runs=%d timeout=%d", url, runs, timeout)
        for idx in range(runs):
            try:
                size, elapsed = self._download_once(url, timeout)
                speed_mb_s = size / elapsed / 1024 / 1024
                results.append(
                    {
                        "size_bytes": size,
                        "elapsed_s": elapsed,
                        "speed_mb_s": speed_mb_s,
                        "error": None,
                    }
                )
                total_bytes += size
                self.logger.debug(
                    "Запрос %d/%d: %.2f МБ за %.3f с (%.2f МБ/с)",
                    idx + 1,
                    runs,
                    size / 1024 / 1024,
                    elapsed,
                    speed_mb_s,
                )
            except RequestError as exc:
                results.append(self._failed_result(exc))
                self.logger.warning("Запрос %d/%d: ОШИБКА — %s", idx + 1, runs, exc)

        ok = [r for r in results if r["error"] is None]
        if ok:
            avg_time = sum(r["elapsed_s"] for r in ok) / len(ok)
            total_time = sum(r["elapsed_s"] for r in ok)
            avg_speed = total_bytes / total_time / 1024 / 1024
        else:
            avg_time = 0.0
            avg_speed = 0.0

        if ok:
            self.logger.debug(
                "measure done ok=%d/%d total_bytes=%d avg_speed=%.2f МБ/с",
                len(ok),
                runs,
                total_bytes,
                avg_speed,
            )
        return {
            "url": url,
            "runs": runs,
            "runs_ok": len(ok),
            "total_bytes": total_bytes,
            "avg_time_s": avg_time,
            "avg_speed_mb_s": avg_speed,
            "per_request": results,
        }
