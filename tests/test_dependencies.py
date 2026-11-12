"""Тесты получения прямых зависимостей."""
import io
import unittest
import urllib.error
from unittest import mock

from depgraph.dependencies import (
    FetchError,
    build_url,
    fetch_metadata,
    get_direct_dependencies,
    parse_requirement,
)

URL = "https://pypi.org/pypi/requests/json"
REQUIRES_DIST = [
    "charset_normalizer<4,>=2",
    "idna<4,>=2.5",
    "PySocks!=1.5.7,>=1.5.6; extra == 'socks'",
    "idna<4,>=2.5",
    "colorama; platform_system == 'Windows'",
]


class ParseRequirementTest(unittest.TestCase):
    """Разбор строк Requires-Dist."""

    def test_name_only(self) -> None:
        """Строка с одним именем."""
        self.assertEqual(parse_requirement("idna"), "idna")

    def test_version_specifier(self) -> None:
        """Имя с ограничением версии."""
        self.assertEqual(parse_requirement("idna<4,>=2.5"), "idna")

    def test_old_style_version(self) -> None:
        """Ограничение версии в скобках."""
        self.assertEqual(parse_requirement("idna (>=2.5)"), "idna")

    def test_extras_in_name(self) -> None:
        """Имя с указанием extras в квадратных скобках."""
        self.assertEqual(parse_requirement("httpx[http2]>=0.2"), "httpx")

    def test_environment_marker(self) -> None:
        """Условие окружения (не extra) не мешает."""
        line = "colorama; platform_system == 'Windows'"
        self.assertEqual(parse_requirement(line), "colorama")

    def test_extra_is_skipped(self) -> None:
        """Зависимость для extra пропускается."""
        line = "PySocks>=1.5.6; extra == 'socks'"
        self.assertIsNone(parse_requirement(line))

    def test_extra_with_other_marker(self) -> None:
        """Extra в составе сложного условия."""
        line = "chardet; python_version < '3.8' and extra == 'x'"
        self.assertIsNone(parse_requirement(line))

    def test_invalid_line(self) -> None:
        """Строка без имени пропускается."""
        self.assertIsNone(parse_requirement("<=1.0"))


class FetchMetadataTest(unittest.TestCase):
    """Загрузка метаданных (сеть заменена заглушкой)."""

    def fetch_with_error(self, error: Exception) -> str:
        """Вызывает fetch_metadata при ошибке сети и даёт текст FetchError."""
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(FetchError) as context:
                fetch_metadata(URL)
        return str(context.exception)

    def test_success(self) -> None:
        """Корректный JSON разбирается в словарь."""
        response = io.BytesIO(b'{"info": {"name": "requests"}}')
        with mock.patch("urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value = response
            result = fetch_metadata(URL)
        self.assertEqual(result["info"]["name"], "requests")

    def test_package_not_found(self) -> None:
        """Ответ 404 означает, что пакета нет."""
        error = urllib.error.HTTPError(URL, 404, "Not Found", {}, None)
        self.assertIn("не найден", self.fetch_with_error(error))

    def test_server_error(self) -> None:
        """Другие HTTP-ошибки сообщают код ответа."""
        error = urllib.error.HTTPError(URL, 500, "Error", {}, None)
        self.assertIn("500", self.fetch_with_error(error))

    def test_no_connection(self) -> None:
        """Сервер недоступен."""
        error = urllib.error.URLError("Connection refused")
        text = self.fetch_with_error(error)
        self.assertIn("не удалось подключиться", text)
        self.assertIn("Connection refused", text)

    def test_timeout(self) -> None:
        """Превышено время ожидания."""
        text = self.fetch_with_error(TimeoutError("timed out"))
        self.assertIn("не удалось подключиться", text)

    def test_invalid_json(self) -> None:
        """Ответ не является JSON."""
        with mock.patch("urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value = io.BytesIO(b"<html>")
            with self.assertRaises(FetchError) as context:
                fetch_metadata(URL)
        self.assertIn("JSON", str(context.exception))


class GetDirectDependenciesTest(unittest.TestCase):
    """Получение списка прямых зависимостей."""

    def get(self, metadata: dict) -> list[str]:
        """Возвращает зависимости для заданных метаданных."""
        with mock.patch("depgraph.dependencies.fetch_metadata",
                        return_value=metadata):
            return get_direct_dependencies("https://pypi.org/pypi", "pkg")

    def test_build_url(self) -> None:
        """Адрес строится с учётом завершающего слеша."""
        self.assertEqual(build_url("https://pypi.org/pypi/", "requests"), URL)

    def test_dependencies(self) -> None:
        """Extra и повторы исключаются, порядок сохраняется."""
        metadata = {"info": {"requires_dist": REQUIRES_DIST}}
        self.assertEqual(self.get(metadata),
                         ["charset_normalizer", "idna", "colorama"])

    def test_no_dependencies(self) -> None:
        """Если requires_dist равен null, зависимостей нет."""
        self.assertEqual(self.get({"info": {"requires_dist": None}}), [])

    def test_no_info(self) -> None:
        """В ответе нет нужных данных."""
        with self.assertRaises(FetchError):
            self.get({"message": "oops"})
