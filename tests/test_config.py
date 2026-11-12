"""Тесты чтения и проверки конфигурационного файла."""
from depgraph.config import Config, ConfigError, load_config
from support import TempDirTestCase

EXPECTED_PROBLEMS = 3


class LoadConfigTest(TempDirTestCase):
    """Проверка успешного чтения параметров."""

    def test_valid_config(self) -> None:
        """Корректный файл даёт заполненный объект Config."""
        config = load_config(self.make_ini(ascii_tree="true"))
        expected = Config("requests", "https://pypi.org/pypi",
                          False, True, 3)
        self.assertEqual(config, expected)

    def test_test_mode_with_existing_file(self) -> None:
        """В тестовом режиме принимается путь к существующему файлу."""
        graph = self.write("A: B\n", "graph.txt")
        ini = self.make_ini(
            package_name="A", repository=str(graph), test_mode="true")
        config = load_config(ini)
        self.assertTrue(config.test_mode)
        self.assertEqual(config.repository, str(graph))

    def test_url_with_percent_sign(self) -> None:
        """Символ % в URL не воспринимается как интерполяция."""
        ini = self.make_ini(repository="https://example.org/a%20b/pypi")
        self.assertEqual(load_config(ini).repository,
                         "https://example.org/a%20b/pypi")

    def test_bool_is_case_insensitive(self) -> None:
        """Значения true и false не зависят от регистра."""
        ini = self.make_ini(ascii_tree="TRUE")
        self.assertTrue(load_config(ini).ascii_tree)

    def test_utf8_bom_is_accepted(self) -> None:
        """Файл с BOM (Блокнот Windows) читается корректно."""
        text = "\ufeff[dependency-graph]\npackage_name = flask\n"
        text += "repository = http://localhost:8080\ntest_mode = false\n"
        text += "ascii_tree = false\nmax_depth = 2\n"
        path = self.write(text)
        self.assertEqual(load_config(path).package_name, "flask")


class FileErrorsTest(TempDirTestCase):
    """Ошибки, связанные с самим INI-файлом."""

    def test_missing_file(self) -> None:
        """Отсутствующий файл конфигурации."""
        self.assertIn("не найден", self.error_text(self.directory / "no.ini"))

    def test_directory_instead_of_file(self) -> None:
        """Вместо файла указана папка."""
        self.assertIn("не удалось прочитать", self.error_text(self.directory))

    def test_invalid_syntax(self) -> None:
        """Файл без заголовка секции."""
        path = self.write("package_name = requests\n")
        text = self.error_text(path)
        self.assertIn("некорректный INI-файл", text)
        self.assertIn("заголовок секции", text)

    def test_duplicate_key(self) -> None:
        """Повторяющийся параметр в секции."""
        path = self.write("[dependency-graph]\nmax_depth = 1\nmax_depth = 2\n")
        self.assertIn("некорректный INI-файл", self.error_text(path))

    def test_missing_section(self) -> None:
        """В файле нет нужной секции."""
        path = self.write("[other]\nmax_depth = 1\n")
        self.assertIn("нет секции", self.error_text(path))

    def test_not_utf8(self) -> None:
        """Файл в кодировке, отличной от UTF-8."""
        path = self.directory / "config.ini"
        path.write_bytes("[dependency-graph]\nx = ю".encode("cp1251"))
        self.assertIn("UTF-8", self.error_text(path))


class ParamErrorsTest(TempDirTestCase):
    """Ошибки значений отдельных параметров."""

    def check(self, fragment: str, **overrides: str | None) -> None:
        """Проверяет, что в сообщении об ошибке есть нужный фрагмент."""
        self.assertIn(fragment, self.error_text(self.make_ini(**overrides)))

    def test_missing_param(self) -> None:
        """Отсутствует обязательный параметр."""
        self.check("отсутствует параметр 'max_depth'", max_depth=None)

    def test_unknown_param(self) -> None:
        """Лишний параметр (например, опечатка в имени)."""
        self.check("неизвестный параметр 'max_dept'", max_dept="3")

    def test_empty_package_name(self) -> None:
        """Пустое имя пакета."""
        self.check("package_name: значение не должно", package_name="")

    def test_bad_package_name(self) -> None:
        """Недопустимые символы в имени пакета."""
        self.check("недопустимое имя пакета", package_name="bad name!")

    def test_lowercase_name_in_test_mode(self) -> None:
        """В тестовом режиме имя должно состоять из больших букв."""
        graph = self.write("A: B\n", "graph.txt")
        self.check("большие латинские буквы", package_name="a",
                   repository=str(graph), test_mode="true")

    def test_empty_repository(self) -> None:
        """Пустой адрес репозитория."""
        self.check("repository: значение не должно", repository="")

    def test_bad_url_scheme(self) -> None:
        """Адрес не http и не https."""
        self.check("ожидается URL", repository="ftp://example.org/pypi")

    def test_url_without_host(self) -> None:
        """Адрес без имени хоста."""
        self.check("ожидается URL", repository="https://")

    def test_url_with_bad_port(self) -> None:
        """Адрес с нечисловым портом."""
        self.check("некорректный URL", repository="http://host:abc/x")

    def test_url_in_test_mode(self) -> None:
        """В тестовом режиме URL вместо пути к файлу."""
        self.check("не найден", package_name="A", test_mode="true")

    def test_test_file_is_directory(self) -> None:
        """В тестовом режиме указана папка."""
        self.check("не является файлом", package_name="A",
                   repository=str(self.directory), test_mode="true")

    def test_path_in_normal_mode(self) -> None:
        """В обычном режиме указан путь к файлу вместо URL."""
        self.check("ожидается URL", repository="/tmp/graph.txt")

    def test_bad_test_mode(self) -> None:
        """Логический параметр с недопустимым значением."""
        self.check("test_mode: ожидается true или false", test_mode="yes")

    def test_bad_ascii_tree(self) -> None:
        """Логический параметр ascii_tree с недопустимым значением."""
        self.check("ascii_tree: ожидается true или false", ascii_tree="2")

    def test_depth_not_integer(self) -> None:
        """Глубина — не целое число."""
        self.check("max_depth: ожидается целое число", max_depth="3.5")

    def test_depth_empty(self) -> None:
        """Глубина не задана."""
        self.check("max_depth: ожидается целое число", max_depth="")

    def test_depth_zero(self) -> None:
        """Глубина равна нулю."""
        self.check("не меньше 1", max_depth="0")

    def test_depth_negative(self) -> None:
        """Отрицательная глубина."""
        self.check("не меньше 1", max_depth="-2")

    def test_all_problems_are_reported_together(self) -> None:
        """Все ошибки сообщаются за один запуск."""
        path = self.make_ini(package_name="", max_depth="x", test_mode="?")
        with self.assertRaises(ConfigError) as context:
            load_config(path)
        self.assertEqual(len(context.exception.problems), EXPECTED_PROBLEMS)
