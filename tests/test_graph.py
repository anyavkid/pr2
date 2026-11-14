"""Тесты построения графа (BFS с рекурсией) и тестового репозитория."""
import tempfile
import unittest
from pathlib import Path

from depgraph.errors import SourceError
from depgraph.graph import build_graph
from depgraph.maven import MavenSource
from depgraph.testrepo import load_repository_file
from helpers import APP, LIBA, LIBB, LIBC, LOCAL_REPO


def make_repo(text):
    """Создать FileRepository из текста во временном файле."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "repo.txt"
        path.write_text(text, encoding="utf-8")
        return load_repository_file(path)


class TestRepositoryFormat(unittest.TestCase):
    """Разбор файла тестового репозитория."""

    def test_parse(self):
        """Комментарии и пустые строки игнорируются."""
        repo = make_repo("# c\nA: B C  # x\n\nB:\n")
        self.assertEqual(repo.dependencies("A"), ["B", "C"])
        self.assertEqual(repo.dependencies("B"), [])

    def test_lowercase_rejected(self):
        """Строчные буквы недопустимы."""
        with self.assertRaises(SourceError):
            make_repo("a: B\n")

    def test_missing_colon(self):
        """Строка без двоеточия — ошибка."""
        with self.assertRaises(SourceError):
            make_repo("A B\n")

    def test_duplicate(self):
        """Повторное описание пакета — ошибка."""
        with self.assertRaises(SourceError):
            make_repo("A: B\nA: C\n")

    def test_unknown_package(self):
        """Запрос неописанного пакета — SourceError."""
        with self.assertRaises(SourceError):
            make_repo("A:\n").dependencies("Z")


class GraphTest(unittest.TestCase):
    """Построение графа на тестовых репозиториях."""

    def test_tree(self):
        """Простое дерево."""
        repo = make_repo("A: B C\nB: D\nC:\nD:\n")
        graph = build_graph("A", repo.dependencies)
        self.assertEqual(
            graph, {"A": ["B", "C"], "B": ["D"], "C": [], "D": []}
        )

    def test_bfs_order(self):
        """Узлы идут по слоям: сначала все дети A, затем внуки."""
        repo = make_repo("A: B C\nB: D\nC: E\nD:\nE:\n")
        graph = build_graph("A", repo.dependencies)
        self.assertEqual(list(graph), ["A", "B", "C", "D", "E"])

    def test_cycle(self):
        """Цикл не зацикливает обход, ребро цикла сохраняется."""
        repo = make_repo("A: B\nB: C\nC: A\n")
        graph = build_graph("A", repo.dependencies)
        self.assertEqual(graph, {"A": ["B"], "B": ["C"], "C": ["A"]})

    def test_self_dependency(self):
        """Самозависимость обрабатывается."""
        repo = make_repo("A: A B\nB:\n")
        graph = build_graph("A", repo.dependencies)
        self.assertEqual(graph["A"], ["A", "B"])

    def test_diamond_expanded_once(self):
        """Общий узел раскрывается один раз."""
        calls = []
        repo = make_repo("A: B C\nB: D\nC: D\nD:\n")

        def get_deps(name):
            """Записать вызов и вернуть зависимости."""
            calls.append(name)
            return repo.dependencies(name)

        build_graph("A", get_deps)
        self.assertEqual(sorted(calls), ["A", "B", "C", "D"])

    def test_filter(self):
        """Пакеты с подстрокой в имени исключаются вместе с поддеревом."""
        repo = make_repo("AB: XB C\nXB: D\nC:\nD:\n")
        graph = build_graph("AB", repo.dependencies, "X")
        self.assertEqual(graph, {"AB": ["C"], "C": []})

    def test_root_error_propagates(self):
        """Ошибка корня — исключение."""
        repo = make_repo("A:\n")
        with self.assertRaises(SourceError):
            build_graph("Z", repo.dependencies)

    def test_missing_child_is_leaf(self):
        """Недоступный не-корневой пакет становится листом."""
        repo = make_repo("A: B\n")
        graph = build_graph("A", repo.dependencies)
        self.assertEqual(graph, {"A": ["B"], "B": []})


class MavenGraphTest(unittest.TestCase):
    """Граф на локальном Maven-репозитории (с циклом liba <-> libc)."""

    def test_graph(self):
        """Транзитивный граф и цикл в Maven-режиме."""
        source = MavenSource(LOCAL_REPO)
        graph = build_graph(APP, source.dependencies)
        self.assertEqual(graph[APP], [LIBA, LIBB])
        self.assertEqual(graph[LIBA], [LIBC, LIBB])
        self.assertEqual(graph[LIBC], [LIBA])

    def test_filter(self):
        """Фильтр исключает libb."""
        source = MavenSource(LOCAL_REPO)
        graph = build_graph(APP, source.dependencies, "libb")
        self.assertNotIn(LIBB, graph)


if __name__ == "__main__":
    unittest.main()
