"""Prepara en un paso la base de la demo a partir de un snapshot: importa, procesa con IA y genera borradores.

Uso:
    python scripts/preparar_demo.py --snapshot data/snapshot-dev/real-20261007b --borradores 3
Luego:
    python src/interfaz/app.py --db <ruta que imprime este script>
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.importar_csv import run_import  # noqa: E402
from scripts.procesar_snapshot import process  # noqa: E402


def ruta_para_mostrar(ruta: Path) -> str:
    """Ruta relativa a la raíz del repo con «/», que funciona igual en PowerShell, cmd y bash."""
    try:
        return ruta.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return ruta.resolve().as_posix()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--snapshot", type=Path, required=True, help="Carpeta del snapshot (con processed/)")
    parser.add_argument("--borradores", type=int, default=3, help="Borradores a generar con el modelo local (0 = ninguno)")
    parser.add_argument("--salida", type=Path, default=ROOT / "data" / "local")
    args = parser.parse_args()

    processed = args.snapshot / "processed"
    manifest = json.loads((processed / "manifest.json").read_text(encoding="utf-8"))
    marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    args.salida.mkdir(parents=True, exist_ok=True)
    importada = args.salida / f"demo-{marca}-importada.sqlite"
    final = args.salida / f"demo-{marca}.sqlite"
    run_import(processed / "noticias.csv", processed / "indicadores.csv", importada,
               args.salida / f"demo-{marca}-importacion.json", f"SNAP-{manifest['version'].upper()}",
               manifest["version"], manifest["fecha_corte_utc"], processed / "fuentes.json")
    reporte = process(importada, final, ROOT / "evaluation" / "etiquetas" / "temas.csv",
                      ROOT / "evaluation" / "etiquetas" / "pares.csv", borradores=args.borradores)
    resumen = {
        "base": str(final),
        "casos": reporte.get("casos_creados"),
        "borradores": [(b.get("caso_id"), b.get("estado")) for b in reporte.get("borradores", [])],
        "siguiente_paso": f'python src/interfaz/app.py --db "{ruta_para_mostrar(final)}"',
    }
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    # Dentro del JSON el comando sale con comillas escapadas y no se puede pegar tal cual en PowerShell.
    print()
    print("Siguiente paso (cópialo tal cual):")
    print("  " + resumen["siguiente_paso"])


if __name__ == "__main__":
    main()
