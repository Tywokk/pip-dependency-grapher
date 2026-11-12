"""Тесты вывода графа в виде ASCII-дерева."""
import unittest

from depgraph.tree import format_tree

DIAMOND = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": ["E"], "E": []}


class FormatTreeTest(unittest.TestCase):
    """Проверка форматирования дерева."""

    def test_single_package(self) -> None:
        """Пакет без зависимостей — только корень."""
        self.assertEqual(format_tree({"A": []}, "A"), ["A"])

    def test_chain(self) -> None:
        """Цепочка зависимостей."""
        graph = {"A": ["B"], "B": ["C"], "C": []}
        self.assertEqual(format_tree(graph, "A"),
                         ["A", "`-- B", "    `-- C"])

    def test_shared_dependency(self) -> None:
        """Общая зависимость показывается под каждым родителем."""
        self.assertEqual(format_tree(DIAMOND, "A"), [
            "A",
            "+-- B",
            "|   `-- D",
            "|       `-- E",
            "`-- C",
            "    `-- D",
            "        `-- E",
        ])

    def test_cycle(self) -> None:
        """Пакет, уже встречавшийся на пути, помечается как цикл."""
        graph = {"A": ["B"], "B": ["C"], "C": ["A", "D"], "D": []}
        self.assertEqual(format_tree(graph, "A"), [
            "A",
            "`-- B",
            "    `-- C",
            "        +-- A (цикл)",
            "        `-- D",
        ])

    def test_self_dependency(self) -> None:
        """Пакет, зависящий от себя, помечается как цикл."""
        graph = {"A": ["A", "B"], "B": []}
        self.assertEqual(format_tree(graph, "A"),
                         ["A", "+-- A (цикл)", "`-- B"])

    def test_depth_limit_leaf(self) -> None:
        """Пакеты на границе глубины (без зависимостей в графе) — листья."""
        graph = {"A": ["B"], "B": []}
        self.assertEqual(format_tree(graph, "A"), ["A", "`-- B"])
