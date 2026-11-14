"""Разбор pom.xml без сторонних библиотек."""
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from depgraph.errors import SourceError

PLACEHOLDER = re.compile(r"\$\{([^}]+)\}")
MAX_PASSES = 10
DEFAULT_SCOPE = "compile"


@dataclass(frozen=True)
class RawDependency:
    """Зависимость в том виде, как она записана в pom.xml."""

    group: str
    artifact: str
    version: str
    scope: str
    optional: bool

    @property
    def key(self):
        """Пара (groupId, artifactId)."""
        return (self.group, self.artifact)


@dataclass
class Pom:
    """Нужные нам данные одного pom.xml."""

    group: str
    artifact: str
    version: str
    parent: tuple
    properties: dict = field(default_factory=dict)
    managed: dict = field(default_factory=dict)
    dependencies: list = field(default_factory=list)


def _local(tag):
    """Имя тега без пространства имён."""
    return tag.rsplit("}", 1)[-1]


def _child(element, name):
    """Первый дочерний элемент с данным именем или None."""
    for child in element:
        if _local(child.tag) == name:
            return child
    return None


def _text(element, name, default=""):
    """Текст дочернего элемента без пробелов по краям."""
    child = _child(element, name)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def _parse_parent(root):
    """Координаты родительского pom или None."""
    parent = _child(root, "parent")
    if parent is None:
        return None
    return tuple(
        _text(parent, name) for name in ("groupId", "artifactId", "version")
    )


def _parse_properties(root):
    """Словарь свойств <properties>."""
    element = _child(root, "properties")
    if element is None:
        return {}
    return {_local(item.tag): (item.text or "").strip() for item in element}


def _raw_dependency(item):
    """Превратить элемент <dependency> в RawDependency."""
    return RawDependency(
        group=_text(item, "groupId"),
        artifact=_text(item, "artifactId"),
        version=_text(item, "version"),
        scope=_text(item, "scope", DEFAULT_SCOPE),
        optional=_text(item, "optional").lower() == "true",
    )


def _dependency_list(container):
    """Список зависимостей из блока <dependencies> внутри container."""
    block = _child(container, "dependencies")
    if block is None:
        return []
    return [
        _raw_dependency(item)
        for item in block
        if _local(item.tag) == "dependency"
    ]


def _parse_managed(root):
    """Словарь dependencyManagement: (group, artifact) -> зависимость."""
    management = _child(root, "dependencyManagement")
    if management is None:
        return {}
    return {dep.key: dep for dep in _dependency_list(management)}


def parse_pom(data):
    """Разобрать содержимое pom.xml (bytes) в объект Pom."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise SourceError(f"некорректный pom.xml: {error}") from error
    parent = _parse_parent(root)
    return Pom(
        group=_text(root, "groupId") or (parent[0] if parent else ""),
        artifact=_text(root, "artifactId"),
        version=_text(root, "version") or (parent[2] if parent else ""),
        parent=parent,
        properties=_parse_properties(root),
        managed=_parse_managed(root),
        dependencies=_dependency_list(root),
    )


def substitute(text, properties):
    """Подставить ${свойства} в строку (с вложенными подстановками)."""
    for _ in range(MAX_PASSES):
        replaced = PLACEHOLDER.sub(
            lambda found: properties.get(found.group(1), found.group(0)),
            text,
        )
        if replaced == text:
            break
        text = replaced
    return text
