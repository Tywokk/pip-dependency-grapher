"""Тесты построения графа зависимостей обходом в ширину."""
import unittest

from depgraph.graph import build_graph, format_graph, reverse_graph

DIAMOND = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
CYCLE = {"A": ["B"], "B": ["C"], "C": ["A"]}
CHAIN_LENGTH = 5000


class BuildGraphTest(unittest.TestCase):
    """Проверка build_graph на разных формах графа."""

    def build(self, data: dict, start: str, depth: int) -> dict:
        """Строит граф по словарю зависимостей и запоминает запросы."""
        self.requested = []

        def get_dependencies(package: str) -> list[str]:
            """Возвращает зависимости пакета из словаря и запоминает запрос."""
            self.requested.append(package)
            return data.get(package, [])

        return build_graph(start, depth, get_dependencies)

    def test_full_graph(self) -> None:
        """Граф без ограничения глубины содержит все пакеты."""
        graph = self.build(DIAMOND, "A", 10)
        self.assertEqual(graph, DIAMOND)

    def test_depth_one_is_direct_dependencies(self) -> None:
        """При глубине 1 раскрывается только начальный пакет."""
        graph = self.build(DIAMOND, "A", 1)
        self.assertEqual(graph, {"A": ["B", "C"], "B": [], "C": []})

    def test_boundary_packages_are_not_requested(self) -> None:
        """Зависимости пакетов на границе глубины не запрашиваются."""
        self.build(DIAMOND, "A", 2)
        self.assertEqual(sorted(self.requested), ["A", "B", "C"])

    def test_shared_dependency_requested_once(self) -> None:
        """Общая зависимость обрабатывается один раз."""
        self.build(DIAMOND, "A", 10)
        self.assertEqual(self.requested.count("D"), 1)

    def test_bfs_order(self) -> None:
        """Пакеты обходятся по уровням."""
        data = {"A": ["B", "C"], "B": ["D"], "C": ["E"]}
        self.build(data, "A", 10)
        self.assertEqual(self.requested, ["A", "B", "C", "D", "E"])

    def test_cycle(self) -> None:
        """Цикл не приводит к зацикливанию, ребро возврата сохраняется."""
        graph = self.build(CYCLE, "A", 10)
        self.assertEqual(graph, CYCLE)
        self.assertEqual(sorted(self.requested), ["A", "B", "C"])

    def test_self_dependency(self) -> None:
        """Пакет, зависящий сам от себя."""
        graph = self.build({"A": ["A", "B"]}, "A", 10)
        self.assertEqual(graph, {"A": ["A", "B"], "B": []})

    def test_no_dependencies(self) -> None:
        """У пакета нет зависимостей."""
        self.assertEqual(self.build({}, "A", 3), {"A": []})

    def test_long_chain_without_recursion(self) -> None:
        """Очень длинная цепочка обрабатывается без рекурсии."""
        def next_package(package: str) -> list[str]:
            """Каждый пакет зависит от следующего номера."""
            return [str(int(package) + 1)]

        graph = build_graph("0", CHAIN_LENGTH, next_package)
        self.assertEqual(len(graph), CHAIN_LENGTH + 1)


class ReverseGraphTest(unittest.TestCase):
    """Проверка обращения рёбер графа."""

    def test_diamond(self) -> None:
        """Для каждого пакета перечислены пакеты, которые от него зависят."""
        self.assertEqual(
            reverse_graph(DIAMOND),
            {"A": [], "B": ["A"], "C": ["A"], "D": ["B", "C"]})

    def test_cycle(self) -> None:
        """Обращение графа с циклом."""
        self.assertEqual(
            reverse_graph(CYCLE), {"A": ["C"], "B": ["A"], "C": ["B"]})

    def test_self_dependency(self) -> None:
        """Пакет, зависящий от себя, зависит от себя и в обращённом графе."""
        graph = {"A": ["A"]}
        self.assertEqual(reverse_graph(graph), {"A": ["A"]})

    def test_bfs_over_reversed_graph(self) -> None:
        """Обход обращённого графа даёт транзитивные обратные зависимости."""
        reverse = reverse_graph(DIAMOND)
        graph = build_graph("D", 10, lambda package: reverse[package])
        self.assertEqual(graph, {"D": ["B", "C"], "B": ["A"], "C": ["A"],
                                 "A": []})


class FormatGraphTest(unittest.TestCase):
    """Проверка текстового представления графа."""

    def test_format(self) -> None:
        """Пакет выводится в виде «A: B C», без зависимостей — «D:»."""
        lines = format_graph({"A": ["B", "C"], "B": [], "C": []})
        self.assertEqual(lines, ["A: B C", "B:", "C:"])
