"""Тесты вывода Mermaid и интерфейса командной строки."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from depgraph.cli import main
from depgraph.mermaid import to_mermaid
from helpers import LOCAL_REPO


class MermaidTest(unittest.TestCase):
    """Формат диаграммы."""

    def test_simple(self):
        """Узлы и рёбра выводятся в ожидаемом виде."""
        graph = {"A": ["B"], "B": []}
        self.assertEqual(
            to_mermaid(graph),
            'graph TD\n    n0["A"]\n    n1["B"]\n    n0 --> n1',
        )

    def test_maven_names(self):
        """Имена с «:» и «.» попадают в подписи, а не в идентификаторы."""
        text = to_mermaid({"org.a:b:1": []})
        self.assertIn('n0["org.a:b:1"]', text)

    def test_quote_escaped(self):
        """Кавычки в подписи экранируются."""
        self.assertIn("#quot;", to_mermaid({'a"b': []}))

    def test_cycle(self):
        """Цикл превращается в рёбра в обе стороны."""
        text = to_mermaid({"A": ["B"], "B": ["A"]})
        self.assertIn("n0 --> n1", text)
        self.assertIn("n1 --> n0", text)


class CliTest(unittest.TestCase):
    """Запуск main() целиком."""

    def setUp(self):
        """Подготовить временную папку."""
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.root = Path(self._dir.name)

    def run_cli(self, ini, mode):
        """Выполнить main и вернуть (код, stdout, stderr)."""
        path = self.root / "c.ini"
        path.write_text(ini, encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["-c", str(path), "-s", mode])
        return code, out.getvalue(), err.getvalue()

    def maven_ini(self, repository=LOCAL_REPO):
        """INI для Maven-режима."""
        return (
            "[depgraph]\npackage = org.example:app:1.0\n"
            f"repository = {repository}\n"
        )

    def test_config_mode(self):
        """Режим config печатает пары ключ-значение."""
        code, out, _ = self.run_cli(self.maven_ini(), "config")
        self.assertEqual(code, 0)
        self.assertIn("package = org.example:app:1.0", out)
        self.assertIn("test_mode = false", out)

    def test_mermaid_mode(self):
        """Режим mermaid печатает диаграмму."""
        code, out, _ = self.run_cli(self.maven_ini(), "mermaid")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("graph TD"))

    def test_error_exit_code(self):
        """Ошибка конфигурации — код 1 и сообщение в stderr."""
        code, _, err = self.run_cli("[depgraph]\n", "graph")
        self.assertEqual(code, 1)
        self.assertIn("Ошибка", err)

    def test_unreachable_repository(self):
        """Недоступный репозиторий — аккуратная ошибка, не traceback."""
        bad = (self.root / "nowhere").as_uri()
        code, _, err = self.run_cli(self.maven_ini(bad), "direct")
        self.assertEqual(code, 1)
        self.assertIn("Ошибка", err)

    def test_test_mode(self):
        """Тестовый режим читает файл репозитория."""
        repo = self.root / "repo.txt"
        repo.write_text("A: B\nB: A\n", encoding="utf-8")
        ini = (
            f"[depgraph]\npackage = A\nrepository = {repo}\n"
            "test_mode = true\n"
        )
        code, out, _ = self.run_cli(ini, "graph")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip().splitlines(), ["A -> B", "B -> A"])


if __name__ == "__main__":
    unittest.main()
