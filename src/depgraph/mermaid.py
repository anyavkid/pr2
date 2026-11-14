"""Текстовое представление графа на языке диаграмм Mermaid."""

HEADER = "graph TD"
INDENT = "    "
QUOTE = '"'
QUOTE_ENTITY = "#quot;"


def _label(name):
    """Подпись узла с экранированными кавычками."""
    return name.replace(QUOTE, QUOTE_ENTITY)


def to_mermaid(graph):
    """Описание графа «пакет -> зависимости» в формате Mermaid (flowchart).

    Идентификаторы узлов — n0, n1, ...; исходные имена идут в подписи,
    так как «:» и «.» в идентификаторах Mermaid недопустимы.
    """
    ids = {name: f"n{index}" for index, name in enumerate(graph)}
    lines = [HEADER]
    for name, node_id in ids.items():
        lines.append(f'{INDENT}{node_id}["{_label(name)}"]')
    for name, children in graph.items():
        for child in children:
            lines.append(f"{INDENT}{ids[name]} --> {ids[child]}")
    return "\n".join(lines)
