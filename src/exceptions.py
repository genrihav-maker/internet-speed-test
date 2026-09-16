"""Типовые исключения сервиса."""

__all__ = ("RequestError",)


class RequestError(Exception):
    """Ошибка выполнения одиночного сетевого/HTTP запроса.

    Поднимается из MainModule._download_once и оборачивает httpx.HTTPError
    (сеть, таймаут, HTTP-статус).
    """
