"""Чтение файла описания графа тестового репозитория.

Формат файла: одна строка на пакет, вида «A: B C» (пакет A зависит от
B и C) или «D:» (зависимостей нет). Имена пакетов состоят из больших
латинских букв. Пустые строки пропускаются.
"""
import re
from pathlib import Path

from depgraph.dependencies import FetchError

NAME_RE = re.compile(r"[A-Z]+")


def parse_line(line: str, number: int) -> tuple[str, list[str]]:
    """Разбирает строку «A: B C» на пакет и список его зависимостей."""
    name, colon, rest = line.partition(":")
    if not colon:
        raise FetchError(f"строка {number}: ожидается формат 'A: B C'")
    names = [name.strip(), *rest.split()]
    for item in names:
        if not NAME_RE.fullmatch(item):
            raise FetchError(
                f"строка {number}: имя '{item}' должно состоять "
                f"из больших латинских букв"
            )
    return names[0], names[1:]


def parse_test_repository(text: str) -> dict[str, list[str]]:
    """Разбирает текст описания графа в словарь «пакет: зависимости».

    Пакеты, которые только упомянуты в зависимостях, получают пустой список.
    """
    graph = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            package, dependencies = parse_line(line, number)
            graph[package] = dependencies
    for dependencies in list(graph.values()):
        for name in dependencies:
            graph.setdefault(name, [])
    return graph


def read_test_repository(path: str) -> dict[str, list[str]]:
    """Читает файл тестового репозитория и разбирает его."""
    try:
        text = Path(path).expanduser().read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        message = f"не удалось прочитать файл '{path}': {error}"
        raise FetchError(message) from error
    return parse_test_repository(text)


def get_test_dependencies(
    graph: dict[str, list[str]], package: str
) -> list[str]:
    """Возвращает прямые зависимости пакета из тестового репозитория."""
    if package not in graph:
        raise FetchError(f"пакет {package} не найден в тестовом репозитории")
    return graph[package]
