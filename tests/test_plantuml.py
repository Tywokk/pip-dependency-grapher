"""Тесты формирования диаграммы PlantUML."""
import base64
import unittest
import zlib

from depgraph.plantuml import (
    BASE64_ALPHABET,
    PLANTUML_ALPHABET,
    SERVER_URL,
    build_image_url,
    encode_plantuml,
    format_plantuml,
)

DOC_TEXT = "Bob -> Alice : hello"
DOC_ENCODED = "SyfFKj2rKt3CoKnELR1Io4ZDoSa70000"
DECODING = str.maketrans(PLANTUML_ALPHABET[:-1], BASE64_ALPHABET[:-1])


def decode_plantuml(encoded: str) -> str:
    """Раскодирует строку так же, как это делает сервер PlantUML."""
    data = base64.b64decode(encoded.translate(DECODING))
    return zlib.decompressobj(-zlib.MAX_WBITS).decompress(data).decode()


class FormatPlantumlTest(unittest.TestCase):
    """Текст диаграммы по графу зависимостей."""

    def test_graph(self) -> None:
        """Компоненты объявлены, зависимости — стрелки."""
        graph = {"A": ["B", "C"], "B": ["C"], "C": []}
        self.assertEqual(format_plantuml(graph).splitlines(), [
            "@startuml",
            "[A]",
            "[B]",
            "[C]",
            "[A] --> [B]",
            "[A] --> [C]",
            "[B] --> [C]",
            "@enduml",
        ])

    def test_single_package(self) -> None:
        """Пакет без зависимостей остаётся на диаграмме."""
        self.assertEqual(format_plantuml({"A": []}),
                         "@startuml\n[A]\n@enduml")

    def test_cycle_edge(self) -> None:
        """Ребро, замыкающее цикл, попадает на диаграмму."""
        text = format_plantuml({"A": ["B"], "B": ["A"]})
        self.assertIn("[B] --> [A]", text)


class EncodeTest(unittest.TestCase):
    """Кодирование текста для адреса сервера PlantUML."""

    def test_documentation_example(self) -> None:
        """Результат совпадает с примером из документации PlantUML."""
        self.assertEqual(encode_plantuml(DOC_TEXT), DOC_ENCODED)

    def test_roundtrip(self) -> None:
        """Закодированный текст раскодируется обратно."""
        text = format_plantuml({"A": ["B"], "B": []})
        self.assertEqual(decode_plantuml(encode_plantuml(text)), text)

    def test_roundtrip_non_ascii(self) -> None:
        """Не-ASCII символы сохраняются."""
        self.assertEqual(decode_plantuml(encode_plantuml("Пакет")), "Пакет")

    def test_url(self) -> None:
        """Адрес состоит из адреса сервера и закодированного текста."""
        self.assertEqual(build_image_url(DOC_TEXT), SERVER_URL + DOC_ENCODED)
