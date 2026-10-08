"""Genera CSV de revisión humana para temas y pares de mismo evento."""
import argparse
import csv
from pathlib import Path
import random
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.procesar_agenda import similarity, tokens
from src.ia.clasificador import clasificar_reglas
from src.ia.agrupacion import dias_separacion


def _sample_stratified(rows, size, seed):
    rng = random.Random(seed)
    buckets = {}
    for row in rows:
        key = (row.get("medio") or "", (row.get("fecha_publicacion") or "")[:10])
        buckets.setdefault(key, []).append(row)
    sample = []
    keys = sorted(buckets)
    while keys and len(sample) < size:
        for key in list(keys):
            bucket = buckets[key]
            if bucket:
                sample.append(bucket.pop(rng.randrange(len(bucket))))
                if len(sample) >= size:
                    break
            if not bucket:
                keys.remove(key)
    return sample


def generar(db_path: Path, salida_dir: Path = Path("evaluation/etiquetas"), seed: int = 42,
            temas_n: int = 300, pares_n: int = 80):
    salida_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in conn.execute("""SELECT id AS id_noticia,titulo,medio,fecha_publicacion,tema
                                                 FROM noticias ORDER BY id""")]
    finally:
        conn.close()
    selected = _sample_stratified(rows, min(temas_n, len(rows)), seed)
    temas_path = salida_dir / "temas-para-revisar.csv"
    with temas_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["id_noticia", "titulo", "medio", "fecha",
                                                    "propuesta_reglas", "propuesta_modelo",
                                                    "etiqueta_humana", "notas"])
        writer.writeheader()
        for row in selected:
            propuesta, _ = clasificar_reglas(row["titulo"])
            writer.writerow({"id_noticia": row["id_noticia"], "titulo": row["titulo"],
                             "medio": row["medio"], "fecha": row.get("fecha_publicacion") or "",
                             "propuesta_reglas": propuesta, "propuesta_modelo": "",
                             "etiqueta_humana": "", "notas": ""})
    pairs = []
    news = [{"id": r["id_noticia"], **r} for r in rows]
    for i, a in enumerate(news):
        for b in news[i + 1:]:
            if dias_separacion(a, b) is not None and dias_separacion(a, b) > 14:
                continue
            score = similarity(tokens(a["titulo"]), tokens(b["titulo"]))
            pairs.append((score, a, b))
    pairs.sort(key=lambda item: item[0], reverse=True)
    high = pairs[:pares_n // 2]
    doubtful = [p for p in pairs if .20 <= p[0] < .55][:pares_n - len(high)]
    chosen = high + doubtful
    pares_path = salida_dir / "pares-para-revisar.csv"
    with pares_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["id_a", "titulo_a", "id_b", "titulo_b",
                                                    "similitud_jaccard", "mismo_evento", "notas"])
        writer.writeheader()
        for score, a, b in chosen:
            writer.writerow({"id_a": a["id"], "titulo_a": a["titulo"], "id_b": b["id"],
                             "titulo_b": b["titulo"], "similitud_jaccard": round(score, 4),
                             "mismo_evento": "", "notas": ""})
    return {"temas": str(temas_path), "filas_temas": len(selected),
            "pares": str(pares_path), "filas_pares": len(chosen),
            "nota": "Las propuestas son ayuda para revisión humana; etiqueta_humana queda vacía."}


def main():
    parser = argparse.ArgumentParser(description="Preparar CSV de etiquetado humano")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--salida", type=Path, default=Path("evaluation/etiquetas"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    import json
    print(json.dumps(generar(args.db, args.salida, args.seed), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
