"""Тесты интерфейса командной строки."""
import contextlib
import io

from depgraph.cli import EXIT_CONFIG_ERROR, EXIT_OK, main
from support import TempDirTestCase


class CliTest(TempDirTestCase):
    """Проверка запуска приложения через main."""

    def run_main(self, *args: str) -> tuple[int, str, str]:
        """Запускает main и возвращает код выхода, stdout и stderr."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_prints_all_params(self) -> None:
        """При запуске выводятся все параметры в формате ключ = значение."""
        ini = self.make_ini(ascii_tree="true", max_depth="5")
        code, out, _ = self.run_main("--config", str(ini))
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(out.splitlines(), [
            "package_name = requests",
            "repository = https://pypi.org/pypi",
            "test_mode = false",
            "ascii_tree = true",
            "max_depth = 5",
        ])

    def test_short_option(self) -> None:
        """Короткая форма опции -c работает так же, как --config."""
        code, out, _ = self.run_main("-c", str(self.make_ini()))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("package_name = requests", out)

    def test_error_goes_to_stderr(self) -> None:
        """Ошибки печатаются в stderr, код выхода ненулевой."""
        ini = self.make_ini(max_depth="0", ascii_tree="maybe")
        code, out, err = self.run_main("--config", str(ini))
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertEqual(out, "")
        self.assertIn("max_depth", err)
        self.assertIn("ascii_tree", err)

    def test_missing_config_file(self) -> None:
        """Несуществующий файл конфигурации."""
        missing = self.directory / "none.ini"
        code, _, err = self.run_main("--config", str(missing))
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("не найден", err)
