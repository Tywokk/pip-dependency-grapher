"""Вывод графа зависимостей в виде ASCII-дерева."""
CYCLE_MARK = " (цикл)"
BRANCH = "+-- "
LAST_BRANCH = "`-- "
VERTICAL = "|   "
EMPTY = "    "


def add_children(
    graph: dict[str, list[str]],
    package: str,
    prefix: str,
    path: list[str],
    lines: list[str],
) -> None:
    """Дописывает в lines поддерево зависимостей пакета.

    path — цепочка пакетов от корня до текущего. Пакет, уже входящий
    в цепочку, помечается как цикл и дальше не раскрывается.
    """
    children = graph[package]
    for index, name in enumerate(children):
        is_last = index == len(children) - 1
        in_cycle = name in path
        branch = LAST_BRANCH if is_last else BRANCH
        mark = CYCLE_MARK if in_cycle else ""
        lines.append(prefix + branch + name + mark)
        if not in_cycle:
            extension = EMPTY if is_last else VERTICAL
            add_children(graph, name, prefix + extension, [*path, name], lines)


def format_tree(graph: dict[str, list[str]], start: str) -> list[str]:
    """Строит ASCII-дерево зависимостей, начиная с пакета start."""
    lines = [start]
    add_children(graph, start, "", [start], lines)
    return lines
