"""Получение прямых зависимостей пакета из репозитория (формат pip)."""
import json
import re
import urllib.error
import urllib.request
from http import HTTPStatus

TIMEOUT_SECONDS = 10
NAME_RE = re.compile(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
EXTRA_RE = re.compile(r"\bextra\b")


class FetchError(Exception):
    """Ошибка получения данных о зависимостях из репозитория."""


def build_url(repository: str, package: str) -> str:
    """Формирует адрес метаданных пакета: <репозиторий>/<пакет>/json."""
    return f"{repository.rstrip('/')}/{package}/json"


def fetch_metadata(url: str) -> dict:
    """Скачивает и разбирает JSON с метаданными пакета."""
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == HTTPStatus.NOT_FOUND:
            message = f"пакет не найден в репозитории: {url}"
        else:
            message = f"сервер вернул ошибку {error.code}: {url}"
        raise FetchError(message) from error
    except OSError as error:
        reason = getattr(error, "reason", error)
        message = f"не удалось подключиться к {url}: {reason}"
        raise FetchError(message) from error
    except ValueError as error:
        message = f"ответ сервера ({url}) не является корректным JSON"
        raise FetchError(message) from error


def extract_requirements(metadata: dict) -> list[str]:
    """Достаёт из метаданных список строк Requires-Dist."""
    try:
        requirements = metadata["info"]["requires_dist"]
    except (KeyError, TypeError) as error:
        raise FetchError("в ответе сервера нет данных о пакете") from error
    return requirements or []


def parse_requirement(line: str) -> str | None:
    """Возвращает имя зависимости из строки Requires-Dist.

    Для зависимостей, нужных только для необязательных возможностей
    пакета (в условии указан extra), возвращает None.
    """
    requirement, _, condition = line.partition(";")
    if EXTRA_RE.search(condition):
        return None
    match = NAME_RE.match(requirement)
    if match is None:
        return None
    return match.group(1)


def get_direct_dependencies(repository: str, package: str) -> list[str]:
    """Возвращает имена прямых зависимостей пакета без повторов."""
    url = build_url(repository, package)
    requirements = extract_requirements(fetch_metadata(url))
    names = []
    for line in requirements:
        name = parse_requirement(line)
        if name is not None and name not in names:
            names.append(name)
    return names
