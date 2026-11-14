"""Тесты порядка загрузки зависимостей."""
import unittest

from depgraph.order import find_cycle_edges, load_order


class OrderTest(unittest.TestCase):
    """Порядок загрузки и поиск циклов."""

    def test_tree(self):
        """Зависимости идут раньше зависящих, корень — последний."""
        graph = {"A": ["B", "C"], "B": ["D"], "C": [], "D": []}
        self.assertEqual(load_order(graph, "A"), ["D", "B", "C", "A"])

    def test_diamond(self):
        """Общая зависимость загружается один раз и до обоих родителей."""
        graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        order = load_order(graph, "A")
        self.assertEqual(order, ["D", "B", "C", "A"])

    def test_cycle(self):
        """Цикл не мешает построить порядок."""
        graph = {"A": ["B"], "B": ["C"], "C": ["A"]}
        self.assertEqual(load_order(graph, "A"), ["C", "B", "A"])

    def test_single(self):
        """Пакет без зависимостей даёт список из себя."""
        self.assertEqual(load_order({"A": []}, "A"), ["A"])

    def test_cycle_edges(self):
        """Ребро, замыкающее цикл, находится."""
        graph = {"A": ["B"], "B": ["C"], "C": ["A"]}
        self.assertEqual(find_cycle_edges(graph, "A"), [("C", "A")])

    def test_no_cycle_edges_in_diamond(self):
        """Ромб — не цикл."""
        graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        self.assertEqual(find_cycle_edges(graph, "A"), [])

    def test_deep_chain_without_recursion(self):
        """Длинная цепочка не упирается в лимит рекурсии."""
        size = 5000
        graph = {str(i): [str(i + 1)] for i in range(size)}
        graph[str(size)] = []
        order = load_order(graph, "0")
        self.assertEqual(order[0], str(size))
        self.assertEqual(order[-1], "0")


if __name__ == "__main__":
    unittest.main()
