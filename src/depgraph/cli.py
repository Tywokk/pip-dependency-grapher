"""Интерфейс командной строки инструмента."""
import argparse
import sys
import webbrowser
from collections.abc import Callable, Sequence
from functools import partial

from depgraph.config import Config, ConfigError, load_config
from depgraph.dependencies import (
    FetchError,
    get_direct_dependencies,
    normalize_name,
)
from depgraph.graph import build_graph
from depgraph.graph_file import get_test_dependencies, read_test_repository
from depgraph.plantuml import build_image_url, format_plantuml
from depgraph.tree import format_tree

PROGRAM_NAME = "depgraph"
DEFAULT_CONFIG = "config.ini"
EXIT_OK = 0
EXIT_FETCH_ERROR = 1
EXIT_CONFIG_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    """Создаёт разбор аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        description="Инструмент визуализации графа зависимостей пакетов.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=DEFAULT_CONFIG,
        help=f"путь к INI-файлу с настройками (по умолчанию {DEFAULT_CONFIG})",
    )
    return parser


def prepare_source(config: Config) -> tuple[str, Callable[[str], list[str]]]:
    """Возвращает имя начального пакета и функцию получения его зависимостей.

    В тестовом режиме зависимости берутся из файла, иначе — из репозитория.
    """
    if config.test_mode:
        graph = read_test_repository(config.repository)
        return config.package_name, partial(get_test_dependencies, graph)
    start = normalize_name(config.package_name)
    return start, partial(get_direct_dependencies, config.repository)


def show_graph(
    graph: dict[str, list[str]], start: str, ascii_tree: bool
) -> None:
    """Выводит граф: текст PlantUML, ASCII-дерево (если включено), картинку.

    Изображение открывается в браузере по адресу сервера PlantUML.
    """
    text = format_plantuml(graph)
    print(text)
    if ascii_tree:
        print("\n".join(format_tree(graph, start)))
    url = build_image_url(text)
    print(f"Изображение графа: {url}")
    webbrowser.open(url)


def report_errors(error: ConfigError) -> None:
    """Печатает найденные проблемы конфигурации в поток ошибок."""
    print("Ошибка конфигурации:", file=sys.stderr)
    for problem in error.problems:
        print(f"  - {problem}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    """Точка входа: читает конфигурацию, строит граф и визуализирует его."""
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        report_errors(error)
        return EXIT_CONFIG_ERROR
    try:
        start, source = prepare_source(config)
        graph = build_graph(start, config.max_depth, source)
    except FetchError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return EXIT_FETCH_ERROR
    show_graph(graph, start, config.ascii_tree)
    return EXIT_OK
