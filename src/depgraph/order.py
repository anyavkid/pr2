"""Порядок загрузки зависимостей: зависимости раньше зависящих."""


def load_order(graph, root):
    """Порядок загрузки пакетов для корня root.

    Обход в глубину без рекурсии, пакет добавляется в результат после всех
    своих зависимостей (обратный топологический порядок). Рёбра, замыкающие
    цикл, игнорируются, поэтому порядок строится и для графов с циклами.
    Корень всегда последний.
    """
    order = []
    visited = {root}
    stack = [(root, iter(graph.get(root, [])))]
    while stack:
        node, children = stack[-1]
        for child in children:
            if child not in visited:
                visited.add(child)
                stack.append((child, iter(graph.get(child, []))))
                break
        else:
            order.append(node)
            stack.pop()
    return order


def find_cycle_edges(graph, root):
    """Рёбра, замыкающие циклы (ведущие в пакет, ещё лежащий на стеке)."""
    edges = []
    on_path = {root}
    visited = {root}
    stack = [(root, iter(graph.get(root, [])))]
    while stack:
        node, children = stack[-1]
        for child in children:
            if child in on_path:
                edges.append((node, child))
            elif child not in visited:
                visited.add(child)
                on_path.add(child)
                stack.append((child, iter(graph.get(child, []))))
                break
        else:
            on_path.discard(node)
            stack.pop()
    return edges
