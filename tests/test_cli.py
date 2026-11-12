"""Тесты интерфейса командной строки."""
import contextlib
import io
from unittest import mock

from depgraph.cli import EXIT_CONFIG_ERROR, EXIT_FETCH_ERROR, EXIT_OK, main
from depgraph.dependencies import FetchError
from support import TempDirTestCase

GET_DEPENDENCIES = "depgraph.cli.get_direct_dependencies"


class CliTest(TempDirTestCase):
    """Проверка запуска приложения через main."""

    def run_main(self, ini, dependencies=None, error=None):
        """Запускает main с заглушкой получения зависимостей."""
        out, err = io.StringIO(), io.StringIO()
        patch = mock.patch(GET_DEPENDENCIES, return_value=dependencies,
                           side_effect=error)
        with patch as getter, contextlib.redirect_stdout(out):
            with contextlib.redirect_stderr(err):
                code = main(["--config", str(ini)])
        return code, out.getvalue(), err.getvalue(), getter

    def test_prints_dependencies(self) -> None:
        """Прямые зависимости выводятся списком."""
        ini = self.make_ini()
        code, out, _, getter = self.run_main(ini, ["idna", "urllib3"])
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(out.splitlines(), [
            "Прямые зависимости пакета requests:",
            "idna",
            "urllib3",
        ])
        getter.assert_called_once_with("https://pypi.org/pypi", "requests")

    def test_no_dependencies(self) -> None:
        """У пакета нет зависимостей."""
        code, out, _, _ = self.run_main(self.make_ini(), [])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("нет прямых зависимостей", out)

    def test_fetch_error(self) -> None:
        """Ошибка получения данных выводится в stderr."""
        code, out, err, _ = self.run_main(
            self.make_ini(), error=FetchError("пакет не найден"))
        self.assertEqual(code, EXIT_FETCH_ERROR)
        self.assertEqual(out, "")
        self.assertIn("пакет не найден", err)

    def test_config_error(self) -> None:
        """Ошибка конфигурации: зависимости не запрашиваются."""
        code, _, err, getter = self.run_main(self.make_ini(max_depth="0"))
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("max_depth", err)
        getter.assert_not_called()

    def test_test_mode_not_supported(self) -> None:
        """Тестовый режим на этом этапе не поддерживается."""
        graph = self.write("A: B\n", "graph.txt")
        ini = self.make_ini(
            package_name="A", repository=str(graph), test_mode="true")
        code, _, err, getter = self.run_main(ini)
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("не реализована", err)
        getter.assert_not_called()
