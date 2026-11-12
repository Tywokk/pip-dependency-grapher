"""Чтение и проверка конфигурационного файла в формате INI."""
import configparser
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

SECTION = "dependency-graph"
PARAM_NAMES = (
    "package_name",
    "repository",
    "test_mode",
    "ascii_tree",
    "max_depth",
)
MIN_DEPTH = 1
URL_SCHEMES = ("http", "https")
BOOL_VALUES = {"true": True, "false": False}
PACKAGE_NAME_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?")
TEST_PACKAGE_RE = re.compile(r"[A-Z]+")
INTEGER_RE = re.compile(r"[+-]?[0-9]+")
SPACE_RE = re.compile(r"\s")


class ConfigError(Exception):
    """Ошибка конфигурации: хранит список всех найденных проблем."""

    def __init__(self, problems: list[str]) -> None:
        """Запоминает список проблем и формирует общий текст ошибки."""
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class Config:
    """Параметры, настраиваемые пользователем."""

    package_name: str
    repository: str
    test_mode: bool
    ascii_tree: bool
    max_depth: int


def read_section(path: Path) -> configparser.SectionProxy:
    """Читает INI-файл и возвращает секцию с параметрами."""
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with open(path, encoding="utf-8-sig") as stream:
            parser.read_file(stream)
    except FileNotFoundError as error:
        raise ConfigError([f"файл конфигурации не найден: {path}"]) from error
    except OSError as error:
        message = f"не удалось прочитать файл '{path}': {error.strerror}"
        raise ConfigError([message]) from error
    except UnicodeDecodeError as error:
        message = f"файл '{path}' не в кодировке UTF-8"
        raise ConfigError([message]) from error
    except configparser.MissingSectionHeaderError as error:
        message = (f"некорректный INI-файл: в строке {error.lineno} "
                   f"ожидается заголовок секции [{SECTION}]")
        raise ConfigError([message]) from error
    except configparser.Error as error:
        message = " ".join(str(error).split())
        raise ConfigError([f"некорректный INI-файл: {message}"]) from error
    if not parser.has_section(SECTION):
        raise ConfigError([f"в файле нет секции [{SECTION}]"])
    return parser[SECTION]


def parse_bool(raw: str, name: str) -> bool:
    """Преобразует значение true или false в логическое."""
    try:
        return BOOL_VALUES[raw.lower()]
    except KeyError:
        raise ValueError(
            f"{name}: ожидается true или false, получено '{raw}'"
        ) from None


def parse_max_depth(raw: str) -> int:
    """Проверяет, что глубина анализа — целое число не меньше минимума."""
    if not INTEGER_RE.fullmatch(raw):
        raise ValueError(f"max_depth: ожидается целое число, получено '{raw}'")
    depth = int(raw)
    if depth < MIN_DEPTH:
        raise ValueError(f"max_depth: значение должно быть не меньше "
                         f"{MIN_DEPTH}, получено {depth}")
    return depth


def parse_package_name(raw: str, test_mode: bool | None) -> str:
    """Проверяет имя пакета с учётом режима работы."""
    if not raw:
        raise ValueError("package_name: значение не должно быть пустым")
    if test_mode is True and not TEST_PACKAGE_RE.fullmatch(raw):
        raise ValueError(f"package_name: в тестовом режиме имя пакета — "
                         f"большие латинские буквы (A, B, ...), получено "
                         f"'{raw}'")
    if test_mode is False and not PACKAGE_NAME_RE.fullmatch(raw):
        raise ValueError(f"package_name: недопустимое имя пакета '{raw}' "
                         f"(латинские буквы, цифры, '.', '_', '-')")
    return raw


def check_url(raw: str) -> None:
    """Проверяет, что строка является корректным адресом http или https."""
    try:
        parts = urlsplit(raw)
        host, _ = parts.hostname, parts.port
    except ValueError:
        raise ValueError(f"repository: некорректный URL '{raw}'") from None
    if parts.scheme not in URL_SCHEMES or not host or SPACE_RE.search(raw):
        raise ValueError(f"repository: ожидается URL вида http(s)://хост/..., "
                         f"получено '{raw}'")


def check_test_file(raw: str) -> None:
    """Проверяет, что путь указывает на читаемый файл тестового репозитория."""
    path = Path(raw).expanduser()
    if not path.exists():
        raise ValueError(f"repository: файл '{raw}' не найден")
    if not path.is_file():
        raise ValueError(f"repository: '{raw}' не является файлом")
    if not os.access(path, os.R_OK):
        raise ValueError(f"repository: нет прав на чтение файла '{raw}'")


def parse_repository(raw: str, test_mode: bool | None) -> str:
    """Проверяет URL или путь к файлу в зависимости от режима работы."""
    if not raw:
        raise ValueError("repository: значение не должно быть пустым")
    if test_mode is True:
        check_test_file(raw)
    elif test_mode is False:
        check_url(raw)
    return raw


def collect(problems: list[str], parser, raw: str | None, *args):
    """Разбирает значение; при ошибке дополняет problems и даёт None."""
    if raw is None:
        return None
    try:
        return parser(raw, *args)
    except (ValueError, OSError) as error:
        problems.append(str(error))
        return None


def fetch_all(section, problems: list[str]) -> dict[str, str | None]:
    """Берёт из секции сырые значения всех параметров."""
    raw = {}
    for name in PARAM_NAMES:
        raw[name] = section.get(name)
        if raw[name] is None:
            problems.append(f"отсутствует параметр '{name}'")
    return raw


def find_unknown_keys(section) -> list[str]:
    """Находит в секции параметры, которых нет в списке допустимых."""
    return [
        f"неизвестный параметр '{key}'"
        for key in section
        if key not in PARAM_NAMES
    ]


def parse_values(section, problems: list[str]) -> dict[str, object]:
    """Разбирает и проверяет значения всех параметров секции."""
    raw = fetch_all(section, problems)
    test_mode = collect(problems, parse_bool, raw["test_mode"], "test_mode")
    return {
        "package_name": collect(
            problems, parse_package_name, raw["package_name"], test_mode),
        "repository": collect(
            problems, parse_repository, raw["repository"], test_mode),
        "test_mode": test_mode,
        "ascii_tree": collect(
            problems, parse_bool, raw["ascii_tree"], "ascii_tree"),
        "max_depth": collect(
            problems, parse_max_depth, raw["max_depth"]),
    }


def load_config(path: str | Path) -> Config:
    """Читает INI-файл и возвращает проверенные параметры.

    Если найдены ошибки, выбрасывает ConfigError со списком всех проблем.
    """
    section = read_section(Path(path))
    problems: list[str] = []
    values = parse_values(section, problems)
    problems.extend(find_unknown_keys(section))
    if problems:
        raise ConfigError(problems)
    return Config(**values)
