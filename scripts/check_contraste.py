"""Puerta WCAG para los tokens visuales de Sourced."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / "src" / "interfaz" / "static" / "tokens.css"

PAIRS = [
    ("tinta/fondo", "--color-tinta", "--color-fondo", 4.5),
    ("tinta/superficie", "--color-tinta", "--color-superficie", 4.5),
    ("secundario/superficie", "--color-secundario", "--color-superficie", 4.5),
    ("primario/superficie", "--color-primario", "--color-superficie", 4.5),
    ("suficiente/superficie", "--color-suficiente", "--color-superficie", 4.5),
    ("parcial/superficie", "--color-parcial", "--color-superficie", 4.5),
    ("insuficiente/superficie", "--color-insuficiente", "--color-superficie", 4.5),
    ("urgente/superficie", "--color-urgente", "--color-superficie", 4.5),
    ("deshabilitado", "--color-deshabilitado-texto", "--color-deshabilitado-fondo", 4.5),
    ("cita", "--color-cita-tinta", "--color-cita-fondo", 4.5),
    ("foco/superficie", "--color-foco", "--color-superficie", 3.0),
]


def parse_blocks(css):
    blocks = {"redaccion": {}, "sala": {}}
    root = re.search(r":root\s*\{(?P<body>.*?)\}\s*\n\s*\[data-tema=\"sala\"\]", css, re.S)
    sala = re.search(r"\[data-tema=\"sala\"\]\s*\{(?P<body>.*?)\}\s*\n\s*@media", css, re.S)
    if not root or not sala:
        raise ValueError("No se encontraron los bloques :root y sala en tokens.css")
    for theme, body in (("redaccion", root.group("body")), ("sala", sala.group("body"))):
        for name, value in re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;", body):
            blocks[theme][name] = value
    merged = {"redaccion": blocks["redaccion"], "sala": dict(blocks["redaccion"])}
    merged["sala"].update(blocks["sala"])
    return merged


def channel(value):
    value = value / 255
    if value <= 0.03928:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def luminance(hex_color):
    raw = hex_color.lstrip("#")
    red, green, blue = (int(raw[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)


def contrast(foreground, background):
    first = luminance(foreground)
    second = luminance(background)
    high, low = max(first, second), min(first, second)
    return (high + 0.05) / (low + 0.05)


def main():
    themes = parse_blocks(TOKENS.read_text(encoding="utf-8"))
    failures = []
    print("Tema       Par                       Ratio  Mínimo  Estado")
    print("---------  ------------------------  -----  ------  ------")
    for theme, tokens in themes.items():
        for label, foreground, background, minimum in PAIRS:
            ratio = contrast(tokens[foreground], tokens[background])
            ok = ratio >= minimum
            print(f"{theme:<9}  {label:<24}  {ratio:>5.2f}  {minimum:>6.1f}  {'OK' if ok else 'FALLA'}")
            if not ok:
                failures.append((theme, label, ratio, minimum))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
