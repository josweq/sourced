"""Puerta estática para T10: el código que corre en la demo no puede salir del equipo.

Uso:
    python scripts/check_sin_red.py            # sale 0 si pasa, 1 si encuentra una salida a la red
    python scripts/check_sin_red.py --raiz <carpeta>

Revisa lo que se ejecuta durante la demo (`src/` y `scripts/smoke_sin_red.py`):
  1. Clientes de red (urllib.request, http.client, socket, requests, httpx, aiohttp, urllib3,
     websocket) solo se permiten en `src/ia/proveedores.py` y en la prueba de humo, que hablan
     con Ollama en 127.0.0.1.
  2. Toda URL literal en .py/.js/.html/.css apunta a 127.0.0.1 o localhost (se excluye el espacio
     de nombres de SVG, que no es una petición).
  3. Los valores por defecto del proveedor son locales: proveedor `ollama` y host 127.0.0.1.
     El adaptador `openai_compat` existe pero solo se activa con LUPA_PROVEEDOR explícito.
La extracción del snapshot (`scripts/extraccion/`) sí usa la red y queda fuera: corre antes,
no durante la demo.
"""
import argparse
from pathlib import Path
import re
import sys

PERMITIDOS_CLIENTE = {"src/ia/proveedores.py", "scripts/smoke_sin_red.py"}
CLIENTES = re.compile(
    r"^\s*(?:import|from)\s+(urllib\.request|http\.client|socket|requests|httpx|aiohttp|urllib3|websocket)\b",
    re.MULTILINE,
)
URL = re.compile(r"https?://[^\s\"'`)<>{}]+")
URL_LOCAL = re.compile(r"^https?://(?:127\.0\.0\.1|localhost)(?::|/|$)")
URL_NO_PETICION = ("http://www.w3.org/2000/svg", "http://www.w3.org/1999/xlink")
EXTENSIONES = {".py", ".js", ".mjs", ".html", ".css"}


def archivos(raiz: Path):
    for ruta in sorted((raiz / "src").rglob("*")):
        if ruta.is_file() and ruta.suffix in EXTENSIONES and "__pycache__" not in ruta.parts:
            yield ruta
    humo = raiz / "scripts" / "smoke_sin_red.py"
    if humo.exists():
        yield humo


def revisar(raiz: Path) -> list[str]:
    fallos = []
    for ruta in archivos(raiz):
        rel = ruta.relative_to(raiz).as_posix()
        texto = ruta.read_text(encoding="utf-8", errors="replace")
        if ruta.suffix == ".py" and rel not in PERMITIDOS_CLIENTE:
            for m in CLIENTES.finditer(texto):
                linea = texto.count("\n", 0, m.start()) + 1
                fallos.append(f"{rel}:{linea}: cliente de red «{m.group(1)}» fuera de los archivos permitidos")
        for m in URL.finditer(texto):
            url = m.group(0)
            if URL_LOCAL.match(url) or url.startswith(URL_NO_PETICION):
                continue
            linea = texto.count("\n", 0, m.start()) + 1
            fallos.append(f"{rel}:{linea}: URL externa «{url}»")
    proveedores = raiz / "src" / "ia" / "proveedores.py"
    if proveedores.exists():
        texto = proveedores.read_text(encoding="utf-8")
        if 'DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"' not in texto:
            fallos.append("src/ia/proveedores.py: el host por defecto de Ollama no es 127.0.0.1")
        if 'os.environ.get("LUPA_PROVEEDOR", "ollama")' not in texto:
            fallos.append("src/ia/proveedores.py: el proveedor por defecto no es ollama")
    else:
        fallos.append("src/ia/proveedores.py: no existe")
    return fallos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    fallos = revisar(args.raiz.resolve())
    if fallos:
        print(f"FALLA  {len(fallos)} posible(s) salida(s) a la red:")
        for f in fallos:
            print(f"  - {f}")
        return 1
    print("OK     sin clientes de red ni URL externas en el código de la demo; proveedor por defecto local")
    return 0


if __name__ == "__main__":
    sys.exit(main())
