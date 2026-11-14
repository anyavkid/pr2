"""Интерфейс командной строки."""
import argparse
import functools
import logging
import sys

from depgraph.config import load_config
from depgraph.errors import DepGraphError
from depgraph.graph import build_graph
from depgraph.maven import MavenSource
from depgraph.order import find_cycle_edges, load_order
from depgraph.testrepo import load_repository_file

EXIT_OK = 0
EXIT_ERROR = 1
DEFAULT_CONFIG = "config.ini"
DEFAULT_MODE = "graph"
FIRST_NUMBER = 1


def show_config(config, get_deps):
    """Строки «ключ = значение» для всех параметров."""
    return [f"{key} = {value}" for key, value in config.as_pairs()]


def show_direct(config, get_deps):
    """Прямые зависимости заданного пакета."""
    return get_deps(config.package)


def format_graph(graph):
    """Строки «пакет -> зависимости» в порядке обхода BFS."""
    lines = []
    for node, children in graph.items():
        target = ", ".join(children) if children else "(нет зависимостей)"
        lines.append(f"{node} -> {target}")
    return lines


def show_graph(config, get_deps):
    """Полный граф зависимостей с учётом транзитивности."""
    graph = build_graph(config.package, get_deps, config.filter_substring)
    return format_graph(graph)


def show_order(config, get_deps):
    """Порядок загрузки: сначала зависимости, в конце сам пакет."""
    graph = build_graph(config.package, get_deps, config.filter_substring)
    order = load_order(graph, config.package)
    lines = [
        f"{number}. {name}"
        for number, name in enumerate(order, FIRST_NUMBER)
    ]
    for source, target in find_cycle_edges(graph, config.package):
        lines.append(f"Цикл: {source} -> {target} (ребро пропущено)")
    return lines


HANDLERS = {
    "config": show_config,
    "direct": show_direct,
    "graph": show_graph,
    "order": show_order,
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
    if config.test_mode:
        source = load_repository_file(config.repository)
    else:
        source = MavenSource(config.repository)
    return functools.lru_cache(maxsize=None)(source.dependencies)


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
