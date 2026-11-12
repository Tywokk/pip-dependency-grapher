"""Интерфейс командной строки инструмента."""
import argparse
import sys
from collections.abc import Sequence

from depgraph.config import Config, ConfigError, load_config

PROGRAM_NAME = "depgraph"
DEFAULT_CONFIG = "config.ini"
EXIT_OK = 0
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


def print_params(config: Config) -> None:
    """Выводит все настраиваемые параметры в формате ключ-значение."""
    for key, value in config.as_pairs():
        print(f"{key} = {value}")


def report_errors(error: ConfigError) -> None:
    """Печатает найденные проблемы конфигурации в поток ошибок."""
    print("Ошибка конфигурации:", file=sys.stderr)
    for problem in error.problems:
        print(f"  - {problem}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    """Точка входа: читает конфигурацию и выводит её параметры."""
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        report_errors(error)
        return EXIT_CONFIG_ERROR
    print_params(config)
    return EXIT_OK
