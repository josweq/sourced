"""Evalua cifras incompatibles en una base derivada, abriendola solo lectura."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ia.contradicciones import detectar, extraer_cifras  # noqa: E402


def evaluar(db_path: Path) -> dict:
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    try:
        casos = db.execute("SELECT snapshot_id,id FROM casos ORDER BY id").fetchall()
        multimedio = 0
        cifras = 0
        contradicciones = []
        for caso in casos:
            evidencias = [dict(r) for r in db.execute("""
              SELECT n.id AS noticia_id,n.titulo,n.medio
              FROM caso_evidencias ce
              JOIN evidencias e ON e.snapshot_id=ce.snapshot_id AND e.id=ce.evidencia_id
              JOIN noticias n ON n.snapshot_id=e.snapshot_id AND n.id=e.noticia_id
              WHERE ce.snapshot_id=? AND ce.caso_id=? ORDER BY n.id
            """, (caso["snapshot_id"], caso["id"]))]
            medios = {str(e.get("medio") or "").casefold() for e in evidencias if e.get("medio")}
            if len(medios) > 1:
                multimedio += 1
            cifras += sum(len(extraer_cifras(e["titulo"])) for e in evidencias)
            hallazgos = detectar(evidencias)
            if hallazgos:
                contradicciones.append({"caso_id": caso["id"], "hallazgos": hallazgos})
        return {"base": str(db_path), "casos": len(casos), "casos_multimedio": multimedio,
                "cifras_extraidas": cifras, "casos_con_contradicciones": len(contradicciones),
                "contradicciones": sum(len(c["hallazgos"]) for c in contradicciones),
                "detalle": contradicciones}
    finally:
        db.close()


def markdown(resultado: dict, comando: str) -> str:
    return "\n".join([
        "# Evaluación T05: contradicciones reales",
        "",
        f"Comando reproducible: `{comando}`",
        "",
        f"- Base: `{resultado['base']}`",
        f"- Casos totales: {resultado['casos']}",
        f"- Casos multimedio: {resultado['casos_multimedio']}",
        f"- Cifras extraídas: {resultado['cifras_extraidas']}",
        f"- Casos con contradicciones: {resultado['casos_con_contradicciones']}",
        f"- Contradicciones detectadas: {resultado['contradicciones']}",
        "",
        "Detalle:",
        "```json",
        json.dumps(resultado["detalle"], ensure_ascii=False, indent=2),
        "```",
        "",
        "Límite: solo titulares y metadatos; no se leyó cuerpo de nota ni fuente primaria.",
        "",
    ])


def main():
    parser = argparse.ArgumentParser(description="Evaluar contradicciones entre medios en casos existentes")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    resultado = evaluar(args.db)
    comando = f"python scripts/evaluar_contradicciones.py --db \"{args.db}\""
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown(resultado, comando), encoding="utf-8")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
