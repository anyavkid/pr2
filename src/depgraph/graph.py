"""Граф зависимостей: обход в ширину (BFS), реализованный рекурсией."""
import logging

from depgraph.errors import SourceError

LOGGER = logging.getLogger(__name__)


class GraphBuilder:
    """Строит граф «пакет -> список зависимостей» послойно.

    Каждый слой BFS обрабатывается одним вызовом _level, который затем
    рекурсивно вызывает себя для следующего слоя. Уже встреченные пакеты
    повторно не раскрываются, поэтому циклы не приводят к зацикливанию,
    но рёбра цикла в графе сохраняются.
    """

    def __init__(self, root, get_deps, substring=""):
        """Задать корень, источник зависимостей и подстроку-фильтр."""
        self.root = root
        self.get_deps = get_deps
        self.substring = substring
        self.graph = {}
        self.seen = {root}

    def build(self):
        """Построить и вернуть граф."""
        self._level([self.root])
        return self.graph

    def _level(self, frontier):
        """Обработать слой и рекурсивно — следующий."""
        following = []
        for node in frontier:
            children = self._children(node)
            self.graph[node] = children
            following.extend(self._fresh(children))
        if following:
            self._level(following)

    def _fresh(self, children):
        """Выбрать ещё не встречавшиеся пакеты и отметить их."""
        fresh = [child for child in children if child not in self.seen]
        self.seen.update(fresh)
        return fresh

    def _children(self, node):
        """Зависимости узла без отфильтрованных пакетов."""
        deps = self._fetch(node)
        if self.substring:
            deps = [dep for dep in deps if self.substring not in dep]
        return list(dict.fromkeys(deps))

    def _fetch(self, node):
        """Получить зависимости; для не-корня сбой даёт лист и warning."""
        try:
            return self.get_deps(node)
        except SourceError as error:
            if node == self.root:
                raise
            LOGGER.warning("%s: зависимости недоступны (%s)", node, error)
            return []


def build_graph(root, get_deps, substring=""):
    """Граф зависимостей пакета root как словарь «пакет -> зависимости»."""
    return GraphBuilder(root, get_deps, substring).build()
