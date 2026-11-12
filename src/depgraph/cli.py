"""Интерфейс командной строки инструмента."""
import argparse
import sys
from collections.abc import Callable, Sequence
from functools import partial

from depgraph.config import Config, ConfigError, load_config
from depgraph.dependencies import (
    FetchError,
    get_direct_dependencies,
    normalize_name,
)
from depgraph.graph import build_graph, format_graph, reverse_graph
from depgraph.graph_file import get_test_dependencies, read_test_repository

PROGRAM_NAME = "depgraph"
DEFAULT_CONFIG = "config.ini"
EXIT_OK = 0
EXIT_FETCH_ERROR = 1
EXIT_CONFIG_ERROR = 2
REVERSE_HEADER = (
    "Обратные зависимости пакета {} "
    "(в строке «X: Y Z» от X зависят Y и Z):"
)
REVERSE_ERROR = (
    "Ошибка: обратные зависимости доступны только в тестовом режиме "
    "(test_mode = true)"
)


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
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="вывести обратные зависимости (только в тестовом режиме)",
    )
    return parser


def prepare_source(
    config: Config, reverse: bool
) -> tuple[str, Callable[[str], list[str]]]:
    """Возвращает имя начального пакета и функцию получения его зависимостей.

    В тестовом режиме зависимости берутся из файла (при reverse — обратные),
    иначе — из репозитория.
    """
    if config.test_mode:
        graph = read_test_repository(config.repository)
        if reverse:
            graph = reverse_graph(graph)
        return config.package_name, partial(get_test_dependencies, graph)
    start = normalize_name(config.package_name)
    return start, partial(get_direct_dependencies, config.repository)


def report_errors(error: ConfigError) -> None:
    """Печатает найденные проблемы конфигурации в поток ошибок."""
    print("Ошибка конфигурации:", file=sys.stderr)
    for problem in error.problems:
        print(f"  - {problem}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    """Точка входа: читает конфигурацию, строит и выводит граф."""
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        report_errors(error)
        return EXIT_CONFIG_ERROR
    if args.reverse and not config.test_mode:
        print(REVERSE_ERROR, file=sys.stderr)
        return EXIT_CONFIG_ERROR
    try:
        start, source = prepare_source(config, args.reverse)
        graph = build_graph(start, config.max_depth, source)
    except FetchError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return EXIT_FETCH_ERROR
    if args.reverse:
        print(REVERSE_HEADER.format(start))
    print("\n".join(format_graph(graph)))
    return EXIT_OK
