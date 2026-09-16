"""Модульная система сервиса: базовый класс OneModule."""

import typing
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main_module import MainModule


class OneModule(ABC):
    """Базовый класс всех модулей сервиса.

    Модуль имеет имя и жизненный цикл: сборка через статический фабричный
    метод build() и освобождение ресурсов в destroy(). Порядок инициализации
    модулей задаёт MainModule через typehint-аннотации.
    """

    def __init__(self, name: str) -> None:
        """Инициализирует модуль.

        Args:
            name: имя модуля.
        """
        self.name = name

    @classmethod
    @abstractmethod
    def build(cls, main_module: "MainModule") -> "OneModule":
        """Собирает и инициализирует модуль.

        Args:
            main_module: MainModule, которому принадлежит модуль.

        Returns:
            Собранный экземпляр модуля.
        """
        ...

    def destroy(self) -> None:  # noqa: B027
        """Освобождает ресурсы модуля при завершении программы.

        По умолчанию ничего не делает.
        """
        pass

    @classmethod
    def fromtypehint(
        cls,
        targetcls: type["MainModule"],
    ) -> dict[str, type["OneModule"]]:
        """Находит модули, объявленные через typehint-аннотации.

        Проходит MRO в обратном порядке, поэтому переопределённые в наследнике
        typehint'ы имеют приоритет. Параметризованные обобщения вида
        Foo[Service] разрешаются через get_origin.

        Args:
            targetcls: класс, у которого ищутся модули.

        Returns:
            Словарь имя модуля -> класс модуля в порядке объявления аннотаций.

        Raises:
            NameError: если аннотация содержит неразрешимую ForwardRef-ссылку.
        """
        hints: dict[str, type[OneModule]] = {}
        for base in reversed(targetcls.__mro__):
            annotations = typing.get_type_hints(base)
            for name, value in annotations.items():
                if not isinstance(value, type):
                    value = typing.get_origin(value)
                if isinstance(value, type) and issubclass(value, cls):
                    hints[name] = value
        return hints

    def __repr__(self) -> str:
        """Возвращает строковое представление модуля.

        Returns:
            Строка вида <ClassName name=...>.
        """
        return f"<{type(self).__name__} name={self.name!r}>"
