"""Построение графа зависимостей обходом в ширину (BFS)."""
from collections import deque
from collections.abc import Callable


def build_graph(
    start: str,
    max_depth: int,
    get_dependencies: Callable[[str], list[str]],
) -> dict[str, list[str]]:
    """Строит граф зависимостей пакета обходом в ширину без рекурсии.

    Граф — словарь «пакет: список его прямых зависимостей». Пакеты на
    глубине max_depth попадают в граф, но их зависимости не запрашиваются.
    Каждый пакет обрабатывается один раз, поэтому циклы не зацикливают обход.
    """
    graph = {}
    visited = {start}
    queue = deque([(start, 0)])
    while queue:
        package, depth = queue.popleft()
        dependencies = []
        if depth < max_depth:
            dependencies = get_dependencies(package)
        graph[package] = dependencies
        for name in dependencies:
            if name not in visited:
                visited.add(name)
                queue.append((name, depth + 1))
    return graph
