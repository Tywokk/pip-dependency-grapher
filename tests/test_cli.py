"""Тесты интерфейса командной строки."""
import contextlib
import io
from pathlib import Path
from unittest import mock

from depgraph.cli import EXIT_CONFIG_ERROR, EXIT_FETCH_ERROR, EXIT_OK, main
from depgraph.dependencies import FetchError
from depgraph.plantuml import SERVER_URL
from support import TempDirTestCase

DATA = Path(__file__).parent / "data"
GET_DEPENDENCIES = "depgraph.cli.get_direct_dependencies"
OPEN_BROWSER = "depgraph.cli.webbrowser.open"
IMAGE_PREFIX = "Изображение графа: " + SERVER_URL
REQUESTS_REPOSITORY = {
    "requests": ["idna", "urllib3"],
    "idna": [],
    "urllib3": ["idna"],
}


class CliTestCase(TempDirTestCase):
    """Общие средства для проверки запуска через main."""

    def run_main(self, ini, source=None):
        """Запускает main с заглушками сети и браузера.

        Возвращает код выхода, stdout и stderr; заглушки доступны как
        self.getter и self.browser.
        """
        out, err = io.StringIO(), io.StringIO()
        with mock.patch(GET_DEPENDENCIES, side_effect=source) as getter:
            with mock.patch(OPEN_BROWSER) as browser:
                with contextlib.redirect_stdout(out):
                    with contextlib.redirect_stderr(err):
                        code = main(["--config", str(ini)])
        self.getter, self.browser = getter, browser
        return code, out.getvalue(), err.getvalue()

    def data_ini(self, name: str, depth: int, **overrides: str) -> Path:
        """Создаёт INI для тестового репозитория из папки tests/data."""
        params = {"package_name": "A", "test_mode": "true",
                  "repository": str(DATA / name), "max_depth": str(depth)}
        return self.make_ini(**{**params, **overrides})


class RealRepositoryTest(CliTestCase):
    """Обычный режим: зависимости запрашиваются из репозитория."""

    def run_requests(self, **overrides: str):
        """Запускает main для пакета requests с заглушкой репозитория."""
        def source(repository: str, package: str) -> list[str]:
            """Возвращает зависимости из заготовленного словаря."""
            return REQUESTS_REPOSITORY[package]

        return self.run_main(self.make_ini(**overrides), source)

    def test_transitive_graph(self) -> None:
        """На диаграмме есть транзитивные зависимости."""
        code, out, _ = self.run_requests()
        self.assertEqual(code, EXIT_OK)
        self.assertIn("[requests] --> [urllib3]", out)
        self.assertIn("[urllib3] --> [idna]", out)

    def test_depth_limit(self) -> None:
        """Глубина 1: зависимости зависимостей не запрашиваются."""
        _, out, _ = self.run_requests(max_depth="1")
        self.assertNotIn("[urllib3] --> [idna]", out)
        self.getter.assert_called_once_with(
            "https://pypi.org/pypi", "requests")

    def test_start_name_is_normalized(self) -> None:
        """Имя начального пакета приводится к нормализованному виду."""
        _, out, _ = self.run_requests(package_name="Requests")
        self.assertIn("[requests]", out)

    def test_fetch_error(self) -> None:
        """Ошибка получения данных выводится в stderr."""
        code, out, err = self.run_main(
            self.make_ini(), FetchError("пакет не найден"))
        self.assertEqual(code, EXIT_FETCH_ERROR)
        self.assertEqual(out, "")
        self.assertIn("пакет не найден", err)
        self.browser.assert_not_called()

    def test_config_error(self) -> None:
        """Ошибка конфигурации: зависимости не запрашиваются."""
        code, _, err = self.run_main(self.make_ini(max_depth="0"))
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("max_depth", err)
        self.getter.assert_not_called()
        self.browser.assert_not_called()


class VisualizationTest(CliTestCase):
    """Тестовый режим: вывод PlantUML, ASCII-дерева и изображения."""

    def lines(self, name: str, depth: int, **overrides: str) -> list[str]:
        """Запускает main на файле из tests/data и даёт строки вывода."""
        code, out, _ = self.run_main(self.data_ini(name, depth, **overrides))
        self.assertEqual(code, EXIT_OK)
        self.getter.assert_not_called()
        return out.splitlines()

    def test_plantuml_text(self) -> None:
        """Выводится текст диаграммы PlantUML."""
        lines = self.lines("diamond.txt", 2)
        self.assertEqual(lines[:6], ["@startuml", "[A]", "[B]", "[C]", "[D]",
                                     "[A] --> [B]"])
        self.assertEqual(lines[9], "@enduml")

    def test_image_is_opened(self) -> None:
        """Адрес изображения выводится и открывается в браузере."""
        lines = self.lines("diamond.txt", 2)
        self.assertTrue(lines[-1].startswith(IMAGE_PREFIX))
        url = lines[-1].removeprefix("Изображение графа: ")
        self.browser.assert_called_once_with(url)

    def test_no_ascii_tree_by_default(self) -> None:
        """Без параметра ascii_tree дерево не выводится."""
        self.assertNotIn("+-- B", self.lines("diamond.txt", 2))

    def test_ascii_tree(self) -> None:
        """При ascii_tree = true выводится ASCII-дерево."""
        lines = self.lines("diamond.txt", 2, ascii_tree="true")
        start = lines.index("@enduml") + 1
        self.assertEqual(lines[start:start + 5], [
            "A", "+-- B", "|   `-- D", "`-- C", "    `-- D"])

    def test_cycle(self) -> None:
        """Цикл: ребро возврата на диаграмме и пометка в дереве."""
        lines = self.lines("cycle.txt", 5, ascii_tree="true")
        self.assertIn("[C] --> [A]", lines)
        self.assertIn("        +-- A (цикл)", lines)

    def test_self_loop(self) -> None:
        """Пакет, зависящий от самого себя."""
        lines = self.lines("self_loop.txt", 5, ascii_tree="true")
        self.assertIn("[A] --> [A]", lines)
        self.assertIn("+-- A (цикл)", lines)

    def test_unknown_start_package(self) -> None:
        """Начального пакета нет в файле."""
        code, _, err = self.run_main(
            self.data_ini("diamond.txt", 3, package_name="Z"))
        self.assertEqual(code, EXIT_FETCH_ERROR)
        self.assertIn("не найден", err)
        self.browser.assert_not_called()

    def test_bad_file_format(self) -> None:
        """Файл с ошибкой формата."""
        code, out, err = self.run_main(self.data_ini("bad_format.txt", 3))
        self.assertEqual(code, EXIT_FETCH_ERROR)
        self.assertEqual(out, "")
        self.assertIn("строка 2", err)
