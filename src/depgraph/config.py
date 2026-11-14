"""Чтение и проверка конфигурационного файла в формате INI."""
import configparser
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from depgraph.errors import ConfigError

SECTION = "depgraph"
KEY_PACKAGE = "package"
KEY_REPOSITORY = "repository"
KEY_TEST_MODE = "test_mode"
KEY_FILTER = "filter"
KNOWN_KEYS = {KEY_PACKAGE, KEY_REPOSITORY, KEY_TEST_MODE, KEY_FILTER}
URL_SCHEMES = ("http", "https", "file")
MAVEN_NAME = re.compile(r"^[^:\s]+:[^:\s]+:[^:\s]+$")
TEST_NAME = re.compile(r"^[A-Z]+$")


@dataclass(frozen=True)
class Config:
    """Параметры, настраиваемые пользователем."""

    package: str
    repository: str
    test_mode: bool
    filter_substring: str

    def as_pairs(self):
        """Вернуть параметры в виде пар «ключ — значение»."""
        return [
            (KEY_PACKAGE, self.package),
            (KEY_REPOSITORY, self.repository),
            (KEY_TEST_MODE, str(self.test_mode).lower()),
            (KEY_FILTER, self.filter_substring),
        ]


def load_config(path):
    """Прочитать INI-файл и вернуть проверенную конфигурацию."""
    parser = configparser.ConfigParser(interpolation=None)
    _read_file(parser, Path(path))
    section = _get_section(parser)
    _check_unknown_keys(section)
    test_mode = _parse_bool(section)
    package = _required(section, KEY_PACKAGE)
    repository = _required(section, KEY_REPOSITORY)
    _check_package(package, test_mode)
    _check_repository(repository, test_mode)
    substring = section.get(KEY_FILTER, "").strip()
    return Config(package, repository, test_mode, substring)


def _read_file(parser, path):
    """Прочитать файл в парсер, превращая сбои в ConfigError."""
    if not path.is_file():
        raise ConfigError(f"файл конфигурации не найден: {path}")
    try:
        with path.open(encoding="utf-8") as stream:
            parser.read_file(stream)
    except (OSError, UnicodeDecodeError) as error:
        raise ConfigError(f"не удалось прочитать {path}: {error}") from error
    except configparser.Error as error:
        raise ConfigError(f"ошибка разбора INI: {error}") from error


def _get_section(parser):
    """Вернуть основную секцию конфигурации."""
    if not parser.has_section(SECTION):
        raise ConfigError(f"отсутствует секция [{SECTION}]")
    return parser[SECTION]


def _check_unknown_keys(section):
    """Запретить неизвестные параметры (защита от опечаток)."""
    unknown = sorted(set(section) - KNOWN_KEYS)
    if unknown:
        raise ConfigError(f"неизвестные параметры: {', '.join(unknown)}")


def _parse_bool(section):
    """Прочитать режим тестирования (по умолчанию выключен)."""
    try:
        return section.getboolean(KEY_TEST_MODE, fallback=False)
    except ValueError as error:
        raise ConfigError(
            f"{KEY_TEST_MODE}: ожидается true или false"
        ) from error


def _required(section, key):
    """Вернуть обязательный непустой параметр."""
    value = section.get(key, "").strip()
    if not value:
        raise ConfigError(f"параметр {key} не задан или пуст")
    return value


def _check_package(package, test_mode):
    """Проверить формат имени пакета для выбранного режима."""
    if test_mode and not TEST_NAME.match(package):
        raise ConfigError(
            f"{KEY_PACKAGE}: в тестовом режиме имя — заглавные латинские "
            f"буквы, получено «{package}»"
        )
    if not test_mode and not MAVEN_NAME.match(package):
        raise ConfigError(
            f"{KEY_PACKAGE}: ожидается groupId:artifactId:version, "
            f"получено «{package}»"
        )


def _check_repository(repository, test_mode):
    """Проверить URL репозитория или путь к файлу тестового репозитория."""
    if test_mode:
        if not Path(repository).is_file():
            raise ConfigError(
                f"{KEY_REPOSITORY}: файл тестового репозитория "
                f"не найден: {repository}"
            )
        return
    parsed = urlparse(repository)
    if parsed.scheme not in URL_SCHEMES:
        raise ConfigError(
            f"{KEY_REPOSITORY}: ожидается URL со схемой "
            f"{'/'.join(URL_SCHEMES)}, получено «{repository}»"
        )
    if not (parsed.netloc or parsed.path):
        raise ConfigError(f"{KEY_REPOSITORY}: в URL нет адреса")
