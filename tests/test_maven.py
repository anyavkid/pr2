"""Тесты разбора pom.xml и получения прямых зависимостей."""
import unittest

from depgraph.errors import SourceError
from depgraph.maven import Coordinate, MavenSource, pom_url
from depgraph.pom import parse_pom, substitute
from helpers import APP, LIBA, LIBB, LIBC, LOCAL_REPO

SIMPLE_POM = b"""<project xmlns="http://maven.apache.org/POM/4.0.0">
  <groupId>g</groupId><artifactId>a</artifactId><version>1</version>
  <dependencies><dependency><groupId>x</groupId>
  <artifactId>y</artifactId><version>2</version></dependency>
  </dependencies></project>"""


class PomTest(unittest.TestCase):
    """Проверки низкоуровневого разбора."""

    def test_parse_namespace(self):
        """pom с пространством имён читается."""
        pom = parse_pom(SIMPLE_POM)
        self.assertEqual(pom.artifact, "a")
        self.assertEqual(pom.dependencies[0].artifact, "y")

    def test_broken_xml(self):
        """Сломанный XML — SourceError."""
        with self.assertRaises(SourceError):
            parse_pom(b"<project>")

    def test_substitute(self):
        """Вложенные свойства подставляются."""
        props = {"a": "${b}", "b": "1.5"}
        self.assertEqual(substitute("v${a}", props), "v1.5")
        self.assertEqual(substitute("${zzz}", props), "${zzz}")

    def test_url(self):
        """URL pom строится по схеме Maven."""
        coord = Coordinate.parse("org.a.b:name:1.2")
        self.assertEqual(
            pom_url("https://r/", coord),
            "https://r/org/a/b/name/1.2/name-1.2.pom",
        )

    def test_bad_coordinate(self):
        """Имя без версии отвергается."""
        with self.assertRaises(SourceError):
            Coordinate.parse("a:b")


class MavenSourceTest(unittest.TestCase):
    """Проверки на локальном репозитории tests/fixtures/repo."""

    def setUp(self):
        """Создать источник поверх file:// репозитория."""
        self.source = MavenSource(LOCAL_REPO)

    def test_direct_dependencies(self):
        """Берутся compile-зависимости; test/provided/optional — нет."""
        self.assertEqual(self.source.dependencies(APP), [LIBA, LIBB])

    def test_managed_version_from_parent(self):
        """Версия libb взята из dependencyManagement родителя."""
        self.assertIn(LIBB, self.source.dependencies(APP))

    def test_property_version(self):
        """${project.version} подставляется."""
        self.assertIn(LIBA, self.source.dependencies(APP))

    def test_transitive_step(self):
        """Зависимости зависимостей читаются тем же способом."""
        self.assertEqual(self.source.dependencies(LIBA), [LIBC, LIBB])

    def test_missing_package(self):
        """Несуществующий пакет — SourceError."""
        with self.assertRaises(SourceError):
            self.source.dependencies("org.example:nope:9")


if __name__ == "__main__":
    unittest.main()
