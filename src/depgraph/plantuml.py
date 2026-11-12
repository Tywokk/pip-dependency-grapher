"""Формирование диаграммы PlantUML и адреса её изображения."""
import base64
import string
import zlib

SERVER_URL = "https://www.plantuml.com/plantuml/svg/"
BASE64_ALPHABET = (
    string.ascii_uppercase + string.ascii_lowercase + string.digits + "+/="
)
PLANTUML_ALPHABET = (
    string.digits + string.ascii_uppercase + string.ascii_lowercase + "-_0"
)
TRANSLATION = str.maketrans(BASE64_ALPHABET, PLANTUML_ALPHABET)


def format_plantuml(graph: dict[str, list[str]]) -> str:
    """Формирует текст диаграммы PlantUML по графу зависимостей.

    Каждый пакет — компонент, каждая зависимость — стрелка от пакета
    к тому, от кого он зависит.
    """
    lines = ["@startuml"]
    lines += [f"[{package}]" for package in graph]
    for package, dependencies in graph.items():
        lines += [f"[{package}] --> [{name}]" for name in dependencies]
    lines.append("@enduml")
    return "\n".join(lines)


def encode_plantuml(text: str) -> str:
    """Сжимает текст (deflate) и кодирует его алфавитом PlantUML."""
    compressor = zlib.compressobj(
        level=zlib.Z_BEST_COMPRESSION, wbits=-zlib.MAX_WBITS)
    data = compressor.compress(text.encode("utf-8")) + compressor.flush()
    encoded = base64.b64encode(data).decode("ascii")
    return encoded.translate(TRANSLATION)


def build_image_url(text: str) -> str:
    """Возвращает адрес изображения диаграммы на сервере PlantUML."""
    return SERVER_URL + encode_plantuml(text)
