"""Тесты чтения и проверки конфигурации."""
import tempfile
import unittest
from pathlib import Path

from depgraph.config import load_config
from depgraph.errors import ConfigError

VALID = """[depgraph]
package = org.example:app:1.0
repository = https://repo.maven.apache.org/maven2
test_mode = false
filter = test
"""


class ConfigTest(unittest.TestCase):
    """Проверка load_config на корректных и ошибочных файлах."""

    def setUp(self):
        """Создать временную папку."""
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.root = Path(self._dir.name)

    def write(self, text):
        """Записать INI-файл и вернуть путь."""
        path = self.root / "config.ini"
        path.write_text(text, encoding="utf-8")
        return path

    def assert_error(self, text, fragment):
        """Убедиться, что загрузка падает с нужным сообщением."""
        with self.assertRaises(ConfigError) as context:
            load_config(self.write(text))
        self.assertIn(fragment, str(context.exception))

    def test_valid(self):
        """Корректный файл читается полностью."""
        config = load_config(self.write(VALID))
        self.assertEqual(config.package, "org.example:app:1.0")
        self.assertFalse(config.test_mode)
        self.assertEqual(config.filter_substring, "test")

    def test_missing_file(self):
        """Отсутствующий файл — ошибка."""
        with self.assertRaises(ConfigError):
            load_config(self.root / "nope.ini")

    def test_missing_section(self):
        """Без секции [depgraph] — ошибка."""
        self.assert_error("[other]\na = b\n", "секция")

    def test_broken_ini(self):
        """Строка без «=» — ошибка разбора."""
        self.assert_error("[depgraph]\nмусор\n", "разбора")

    def test_unknown_key(self):
        """Опечатка в имени параметра — ошибка."""
        self.assert_error(VALID + "pakage = x\n", "неизвестные")

    def test_empty_package(self):
        """Пустое имя пакета — ошибка."""
        self.assert_error(VALID.replace("org.example:app:1.0", ""), "package")

    def test_bad_package_format(self):
        """Имя без версии — ошибка."""
        self.assert_error(VALID.replace(":1.0", ""), "groupId")

    def test_bad_url(self):
        """Репозиторий не URL — ошибка."""
        text = VALID.replace("https://repo.maven.apache.org/maven2", "abc")
        self.assert_error(text, "URL")

    def test_bad_bool(self):
        """Недопустимое значение test_mode — ошибка."""
        self.assert_error(VALID.replace("false", "maybe"), "test_mode")

    def test_test_mode_requires_file(self):
        """В тестовом режиме файл репозитория должен существовать."""
        text = VALID.replace("false", "true").replace(
            "org.example:app:1.0", "A"
        )
        self.assert_error(text, "не найден")

    def test_test_mode_requires_capitals(self):
        """В тестовом режиме имя — заглавные латинские буквы."""
        repo = self.root / "repo.txt"
        repo.write_text("A:\n", encoding="utf-8")
        text = VALID.replace("false", "true").replace(
            "https://repo.maven.apache.org/maven2", str(repo)
        )
        self.assert_error(text, "заглавные")


if __name__ == "__main__":
    unittest.main()
