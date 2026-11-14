"""Тестовый репозиторий: файл с описанием графа большими буквами.

Формат: одна строка на пакет, «A: B C» — A зависит от B и C.
Пустые строки и текст после «#» игнорируются.
"""
import re
from pathlib import Path

from depgraph.errors import SourceError

NAME = re.compile(r"^[A-Z]+$")
FIRST_LINE = 1
COMMENT_MARK = "#"


class FileRepository:
    """Источник зависимостей, читающий таблицу из памяти."""

    def __init__(self, table):
        """Запомнить таблицу «пакет -> список зависимостей»."""
        self.table = table

    def dependencies(self, name):
        """Прямые зависимости пакета из тестового файла."""
        if name not in self.table:
            raise SourceError(f"пакет {name} не описан в тестовом файле")
        return list(self.table[name])


def _check_name(name, number):
    """Проверить, что имя состоит из заглавных латинских букв."""
    if not NAME.match(name):
        raise SourceError(
            f"строка {number}: имя «{name}» должно состоять "
            "из заглавных латинских букв"
        )


def _parse_line(number, line, table):
    """Разобрать одну строку файла и добавить её в таблицу."""
    text = line.split(COMMENT_MARK, 1)[0].strip()
    if not text:
        return
    name, separator, rest = text.partition(":")
    if not separator:
        raise SourceError(f"строка {number}: ожидался формат «A: B C»")
    name = name.strip()
    _check_name(name, number)
    if name in table:
        raise SourceError(f"строка {number}: пакет {name} описан дважды")
    deps = list(dict.fromkeys(rest.split()))
    for dep in deps:
        _check_name(dep, number)
    table[name] = deps


def load_repository_file(path):
    """Прочитать файл тестового репозитория."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise SourceError(f"не удалось прочитать {path}: {error}") from error
    table = {}
    for number, line in enumerate(text.splitlines(), start=FIRST_LINE):
        _parse_line(number, line, table)
    return FileRepository(table)
