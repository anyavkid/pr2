"""Получение прямых зависимостей Maven-пакета из репозитория."""
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

from depgraph.errors import SourceError
from depgraph.pom import PLACEHOLDER, parse_pom, substitute

LOGGER = logging.getLogger(__name__)
TIMEOUT_SECONDS = 15
MAX_PARENT_DEPTH = 10
COORDINATE_PARTS = 3
IGNORED_SCOPES = frozenset({"test", "provided", "system", "import"})
RANGE_MARKS = ("[", "(")


@dataclass(frozen=True)
class Coordinate:
    """Координаты пакета: groupId:artifactId:version."""

    group: str
    artifact: str
    version: str

    def __str__(self):
        """Строковая запись groupId:artifactId:version."""
        return f"{self.group}:{self.artifact}:{self.version}"

    @classmethod
    def parse(cls, text):
        """Разобрать строку groupId:artifactId:version."""
        parts = text.split(":")
        if len(parts) != COORDINATE_PARTS or not all(parts):
            raise SourceError(f"некорректное имя пакета: «{text}»")
        return cls(*parts)


def fetch_bytes(url):
    """Скачать ресурс по URL (http, https или file)."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "depgraph/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as reply:
            return reply.read()
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise SourceError(f"не удалось получить {url}: {error}") from error


def pom_url(repository, coord):
    """URL файла pom для пакета в репозитории Maven."""
    base = repository.rstrip("/")
    folder = coord.group.replace(".", "/")
    name = f"{coord.artifact}-{coord.version}.pom"
    return f"{base}/{folder}/{coord.artifact}/{coord.version}/{name}"


def _load_parent(parent, repository, fetch):
    """Загрузить родительский pom; при сбое вернуть None."""
    coord = Coordinate(*parent)
    try:
        return parse_pom(fetch(pom_url(repository, coord)))
    except SourceError as error:
        LOGGER.warning("родительский pom %s недоступен: %s", coord, error)
        return None


def load_pom_chain(coord, repository, fetch):
    """Цепочка pom: сам пакет и его родители (от ближнего к дальнему)."""
    pom = parse_pom(fetch(pom_url(repository, coord)))
    chain = [pom]
    while pom.parent is not None and len(chain) < MAX_PARENT_DEPTH:
        pom = _load_parent(pom.parent, repository, fetch)
        if pom is None:
            break
        chain.append(pom)
    return chain


def collect_properties(chain):
    """Свойства цепочки pom: дочерние переопределяют родительские."""
    props = {}
    for pom in reversed(chain):
        props.update(pom.properties)
    head = chain[0]
    parent_version = head.parent[2] if head.parent else ""
    props.update({
        "project.groupId": head.group,
        "project.artifactId": head.artifact,
        "project.version": head.version,
        "project.parent.version": parent_version,
        "pom.version": head.version,
        "version": head.version,
    })
    return props


def collect_managed(chain, props):
    """Версии из dependencyManagement всей цепочки pom."""
    managed = {}
    for pom in reversed(chain):
        for (group, artifact), dep in pom.managed.items():
            key = (substitute(group, props), substitute(artifact, props))
            managed[key] = dep.version
    return managed


def _is_range(version):
    """Признак диапазона версий вида [1.0,2.0)."""
    return version.startswith(RANGE_MARKS)


def _resolve(raw, props, managed):
    """Превратить зависимость pom в Coordinate или None, если не нужна."""
    if raw.optional or raw.scope in IGNORED_SCOPES:
        return None
    group = substitute(raw.group, props)
    artifact = substitute(raw.artifact, props)
    version = raw.version or managed.get((group, artifact), "")
    version = substitute(version, props)
    if not version or PLACEHOLDER.search(version) or _is_range(version):
        LOGGER.warning(
            "пропущена %s:%s: версия не определена (%s)",
            group, artifact, version or "пусто",
        )
        return None
    return Coordinate(group, artifact, version)


def direct_dependencies(coord, repository, fetch=fetch_bytes):
    """Прямые зависимости пакета (compile/runtime, без optional)."""
    chain = load_pom_chain(coord, repository, fetch)
    props = collect_properties(chain)
    managed = collect_managed(chain, props)
    result = []
    for raw in chain[0].dependencies:
        dep = _resolve(raw, props, managed)
        if dep is not None and dep not in result:
            result.append(dep)
    return result


class MavenSource:
    """Источник зависимостей: настоящий (или локальный) Maven-репозиторий."""

    def __init__(self, repository, fetch=fetch_bytes):
        """Запомнить адрес репозитория и функцию загрузки."""
        self.repository = repository
        self.fetch = fetch

    def dependencies(self, name):
        """Имена прямых зависимостей пакета groupId:artifactId:version."""
        coord = Coordinate.parse(name)
        deps = direct_dependencies(coord, self.repository, self.fetch)
        return [str(dep) for dep in deps]
