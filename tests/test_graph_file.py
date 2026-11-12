"""Тесты чтения файла тестового репозитория."""
from depgraph.dependencies import FetchError
from depgraph.graph_file import (
    get_test_dependencies,
    parse_test_repository,
    read_test_repository,
)
from support import TempDirTestCase


class ParseTest(TempDirTestCase):
    """Разбор текста описания графа."""

    def error_text(self, text: str) -> str:
        """Возвращает текст ошибки разбора."""
        with self.assertRaises(FetchError) as context:
            parse_test_repository(text)
        return str(context.exception)

    def test_parse(self) -> None:
        """Строки разбираются в словарь, пустые строки пропускаются."""
        graph = parse_test_repository("A: B C\n\nB: C\nC:\n")
        self.assertEqual(graph, {"A": ["B", "C"], "B": ["C"], "C": []})

    def test_only_mentioned_package(self) -> None:
        """Пакет, который только упомянут как зависимость, есть в графе."""
        self.assertEqual(parse_test_repository("A: B\n"),
                         {"A": ["B"], "B": []})

    def test_missing_colon(self) -> None:
        """Строка без двоеточия."""
        text = self.error_text("A: B\nB C\n")
        self.assertIn("строка 2", text)
        self.assertIn("формат", text)

    def test_lowercase_name(self) -> None:
        """Имя пакета не из больших латинских букв."""
        self.assertIn("'b'", self.error_text("A: b\n"))

    def test_empty_package_name(self) -> None:
        """Строка без имени пакета слева от двоеточия."""
        self.assertIn("строка 1", self.error_text(": B\n"))


class ReadTest(TempDirTestCase):
    """Чтение файла и поиск пакета."""

    def test_read_file(self) -> None:
        """Файл читается и разбирается."""
        path = self.write("A: B\n", "graph.txt")
        self.assertEqual(read_test_repository(str(path)),
                         {"A": ["B"], "B": []})

    def test_missing_file(self) -> None:
        """Файла не существует."""
        with self.assertRaises(FetchError) as context:
            read_test_repository(str(self.directory / "none.txt"))
        self.assertIn("не удалось прочитать", str(context.exception))

    def test_get_dependencies(self) -> None:
        """Зависимости известного пакета."""
        self.assertEqual(get_test_dependencies({"A": ["B"], "B": []}, "A"),
                         ["B"])

    def test_unknown_package(self) -> None:
        """Пакета нет в тестовом репозитории."""
        with self.assertRaises(FetchError) as context:
            get_test_dependencies({"A": []}, "Z")
        self.assertIn("не найден", str(context.exception))
