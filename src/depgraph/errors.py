"""Исключения инструмента."""


class DepGraphError(Exception):
    """Базовая ошибка инструмента."""


class ConfigError(DepGraphError):
    """Некорректный конфигурационный файл."""


class SourceError(DepGraphError):
    """Не удалось получить данные о зависимостях."""
