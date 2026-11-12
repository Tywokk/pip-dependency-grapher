"""Общие вспомогательные средства для тестов."""
import functools
import tempfile
import unittest
from pathlib import Path

from depgraph.config import ConfigError, load_config

SECTION_HEADER = "[dependency-graph]"
DEFAULT_PARAMS = {
    "package_name": "requests",
    "repository": "https://pypi.org/pypi",
    "test_mode": "false",
    "ascii_tree": "false",
    "max_depth": "3",
}


class TempDirTestCase(unittest.TestCase):
    """Базовый тест с временной папкой и генерацией INI-файлов."""

    @functools.cached_property
    def directory(self) -> Path:
        """Временная папка теста, которая удаляется после его завершения."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def write(self, text: str, name: str = "config.ini") -> Path:
        """Записывает текст в файл временной папки и возвращает путь."""
        path = self.directory / name
        path.write_text(text, encoding="utf-8")
        return path

    def make_ini(self, **overrides: str | None) -> Path:
        """Создаёт INI-файл; значение None удаляет параметр из файла."""
        params = {**DEFAULT_PARAMS, **overrides}
        lines = [SECTION_HEADER]
        lines += [f"{key} = {value}" for key, value in params.items()
                  if value is not None]
        return self.write("\n".join(lines) + "\n")

    def error_text(self, path: Path) -> str:
        """Возвращает текст ошибки, которую даёт чтение файла."""
        with self.assertRaises(ConfigError) as context:
            load_config(path)
        return "\n".join(context.exception.problems)
