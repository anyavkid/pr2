"""Интерфейс командной строки."""
import argparse
import logging
import sys

from depgraph.config import load_config
from depgraph.errors import DepGraphError
from depgraph.maven import MavenSource

EXIT_OK = 0
EXIT_ERROR = 1
DEFAULT_CONFIG = "config.ini"
DEFAULT_MODE = "config"


def show_config(config, get_deps):
    """Строки «ключ = значение» для всех параметров."""
    return [f"{key} = {value}" for key, value in config.as_pairs()]


def show_direct(config, get_deps):
    """Прямые зависимости заданного пакета."""
    return get_deps(config.package)


HANDLERS = {
    "config": show_config,
    "direct": show_direct,
}


def parse_args(argv):
    """Разобрать аргументы командной строки."""
    parser = argparse.ArgumentParser(
        prog="depgraph",
        description="Граф зависимостей Maven-пакета.",
    )
    parser.add_argument(
        "-c", "--config", default=DEFAULT_CONFIG,
        help="путь к INI-файлу (по умолчанию %(default)s)",
    )
    parser.add_argument(
        "-s", "--show", choices=tuple(HANDLERS), default=DEFAULT_MODE,
        help="что вывести (по умолчанию %(default)s)",
    )
    return parser.parse_args(argv)


def make_get_deps(config):
    """Функция «имя пакета -> список имён прямых зависимостей»."""
    return MavenSource(config.repository).dependencies


def run(args):
    """Выполнить выбранный режим и вернуть строки вывода."""
    config = load_config(args.config)
    return HANDLERS[args.show](config, make_get_deps(config))


def main(argv=None):
    """Запустить приложение и вернуть код возврата."""
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s: %(message)s"
    )
    args = parse_args(argv)
    try:
        lines = run(args)
    except DepGraphError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return EXIT_ERROR
    print("\n".join(lines))
    return EXIT_OK
