"""Интерфейс командной строки инструмента."""
import argparse
import sys
from collections.abc import Sequence

from depgraph.config import ConfigError, load_config
from depgraph.dependencies import FetchError, get_direct_dependencies

PROGRAM_NAME = "depgraph"
DEFAULT_CONFIG = "config.ini"
EXIT_OK = 0
EXIT_FETCH_ERROR = 1
EXIT_CONFIG_ERROR = 2
TEST_MODE_MESSAGE = "Ошибка: работа с тестовым репозиторием пока не реализована"


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


def print_dependencies(package: str, dependencies: list[str]) -> None:
    """Выводит на экран прямые зависимости пакета."""
    if not dependencies:
        print(f"У пакета {package} нет прямых зависимостей")
        return
    print(f"Прямые зависимости пакета {package}:")
    for name in dependencies:
        print(name)


def report_errors(error: ConfigError) -> None:
    """Печатает найденные проблемы конфигурации в поток ошибок."""
    print("Ошибка конфигурации:", file=sys.stderr)
    for problem in error.problems:
        print(f"  - {problem}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    """Точка входа: читает конфигурацию и выводит прямые зависимости."""
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        report_errors(error)
        return EXIT_CONFIG_ERROR
    if config.test_mode:
        print(TEST_MODE_MESSAGE, file=sys.stderr)
        return EXIT_CONFIG_ERROR
    try:
        names = get_direct_dependencies(config.repository, config.package_name)
    except FetchError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return EXIT_FETCH_ERROR
    print_dependencies(config.package_name, names)
    return EXIT_OK
