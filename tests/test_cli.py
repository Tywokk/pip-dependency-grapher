"""Тесты интерфейса командной строки."""
import contextlib
import io
from pathlib import Path
from unittest import mock

from depgraph.cli import EXIT_CONFIG_ERROR, EXIT_FETCH_ERROR, EXIT_OK, main
from depgraph.dependencies import FetchError
from support import TempDirTestCase

DATA = Path(__file__).parent / "data"
GET_DEPENDENCIES = "depgraph.cli.get_direct_dependencies"
REQUESTS_REPOSITORY = {
    "requests": ["idna", "urllib3"],
    "idna": [],
    "urllib3": ["idna"],
}


class CliTestCase(TempDirTestCase):
    """Общие средства для проверки запуска через main."""

    def run_main(self, ini, source=None):
        """Запускает main; source — заглушка получения зависимостей."""
        out, err = io.StringIO(), io.StringIO()
        patch = mock.patch(GET_DEPENDENCIES, side_effect=source)
        with patch as getter, contextlib.redirect_stdout(out):
            with contextlib.redirect_stderr(err):
                code = main(["--config", str(ini)])
        return code, out.getvalue(), err.getvalue(), getter

    def data_ini(self, name: str, depth: int, package: str = "A") -> Path:
        """Создаёт INI для тестового репозитория из папки tests/data."""
        return self.make_ini(package_name=package, test_mode="true",
                             repository=str(DATA / name),
                             max_depth=str(depth))


class RealRepositoryTest(CliTestCase):
    """Обычный режим: зависимости запрашиваются из репозитория."""

    def run_requests(self, **overrides: str):
        """Запускает main для пакета requests с заглушкой репозитория."""
        def source(repository: str, package: str) -> list[str]:
            """Возвращает зависимости из заготовленного словаря."""
            return REQUESTS_REPOSITORY[package]

        return self.run_main(self.make_ini(**overrides), source)

    def test_transitive_graph(self) -> None:
        """Выводится граф с транзитивными зависимостями."""
        code, out, _, _ = self.run_requests()
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(out.splitlines(),
                         ["requests: idna urllib3", "idna:", "urllib3: idna"])

    def test_depth_limit(self) -> None:
        """Глубина 1: зависимости зависимостей не запрашиваются."""
        _, out, _, getter = self.run_requests(max_depth="1")
        self.assertEqual(out.splitlines(),
                         ["requests: idna urllib3", "idna:", "urllib3:"])
        getter.assert_called_once_with("https://pypi.org/pypi", "requests")

    def test_start_name_is_normalized(self) -> None:
        """Имя начального пакета приводится к нормализованному виду."""
        _, out, _, _ = self.run_requests(package_name="Requests")
        self.assertTrue(out.startswith("requests:"))

    def test_fetch_error(self) -> None:
        """Ошибка получения данных выводится в stderr."""
        error = FetchError("пакет не найден")
        code, out, err, _ = self.run_main(self.make_ini(), error)
        self.assertEqual(code, EXIT_FETCH_ERROR)
        self.assertEqual(out, "")
        self.assertIn("пакет не найден", err)

    def test_config_error(self) -> None:
        """Ошибка конфигурации: зависимости не запрашиваются."""
        code, _, err, getter = self.run_main(self.make_ini(max_depth="0"))
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("max_depth", err)
        getter.assert_not_called()


class TestRepositoryTest(CliTestCase):
    """Тестовый режим: граф описан в файле."""

    def graph_lines(self, name: str, depth: int) -> list[str]:
        """Запускает main на файле из tests/data и даёт строки вывода."""
        code, out, _, getter = self.run_main(self.data_ini(name, depth))
        self.assertEqual(code, EXIT_OK)
        getter.assert_not_called()
        return out.splitlines()

    def test_diamond_full(self) -> None:
        """Общая зависимость выводится один раз."""
        self.assertEqual(self.graph_lines("diamond.txt", 5),
                         ["A: B C", "B: D", "C: D", "D: E", "E:"])

    def test_diamond_depth_two(self) -> None:
        """Глубина 2 обрезает граф."""
        self.assertEqual(self.graph_lines("diamond.txt", 2),
                         ["A: B C", "B: D", "C: D", "D:"])

    def test_cycle(self) -> None:
        """Цикл A -> B -> C -> A обрабатывается корректно."""
        self.assertEqual(self.graph_lines("cycle.txt", 5),
                         ["A: B", "B: C", "C: A D", "D:"])

    def test_self_loop(self) -> None:
        """Пакет, зависящий от самого себя."""
        self.assertEqual(self.graph_lines("self_loop.txt", 5),
                         ["A: A B", "B:"])

    def test_start_from_inner_package(self) -> None:
        """Анализ можно начать с любого пакета из файла."""
        ini = self.data_ini("diamond.txt", 5, package="C")
        _, out, _, _ = self.run_main(ini)
        self.assertEqual(out.splitlines(), ["C: D", "D: E", "E:"])

    def test_unknown_start_package(self) -> None:
        """Начального пакета нет в файле."""
        code, _, err, _ = self.run_main(
            self.data_ini("diamond.txt", 3, package="Z"))
        self.assertEqual(code, EXIT_FETCH_ERROR)
        self.assertIn("не найден", err)

    def test_bad_file_format(self) -> None:
        """Файл с ошибкой формата."""
        code, out, err, _ = self.run_main(
            self.data_ini("bad_format.txt", 3))
        self.assertEqual(code, EXIT_FETCH_ERROR)
        self.assertEqual(out, "")
        self.assertIn("строка 2", err)
