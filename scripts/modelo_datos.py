"""Contrato de referencia: sin red, proveedores IA ni dependencias externas."""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"
TABLES = ("snapshots", "fuentes", "noticias", "indicadores", "grupos",
          "grupo_noticias", "evidencias", "casos", "caso_evidencias",
          "priorizaciones", "borradores", "afirmaciones", "citas", "revisiones")
DEFAULT_FIXTURE = ROOT / "tests/fixtures/synthetic/modelo-v1.json"


def utc(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", value
    ):
        raise ValueError(f"Fecha UTC inválida: {value!r}")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_relations(db):
    """Integridad estructural; no establece verdad ni cobertura semántica."""
    allowed = {"noticias": {"titulo", "texto_disponible", "fecha_publicacion", "fecha_deteccion"},
               "indicadores": {"valor", "anio", "unidad", "pais_iso3"}}
    for row in db.execute("SELECT * FROM evidencias"):
        table, id_col = ("noticias", "noticia_id") if row["noticia_id"] else ("indicadores", "indicador_registro_id")
        if row["campo"] not in allowed[table]:
            raise ValueError("Campo de evidencia no permitido")
        record = db.execute(f"SELECT * FROM {table} WHERE snapshot_id=? AND id=?",
                            (row["snapshot_id"], row[id_col])).fetchone()
        if record[row["campo"]] is None:
            raise ValueError("Un valor ausente no puede respaldar una afirmación factual")
        if table == "noticias" and row["campo"] == "texto_disponible" and record["alcance_texto"] == "titular_metadatos":
            raise ValueError("Metadatos no equivalen a texto autorizado")
    missing = db.execute("""
        SELECT a.id FROM afirmaciones a WHERE a.tipo IN ('hecho','declaracion')
        AND NOT EXISTS (SELECT 1 FROM citas c WHERE c.snapshot_id=a.snapshot_id
            AND c.afirmacion_id=a.id AND c.relacion='sustenta')
    """).fetchall()
    if missing:
        raise ValueError("Afirmaciones factuales sin cita de sustento")
    for row in db.execute("SELECT * FROM afirmaciones"):
        draft = db.execute("SELECT * FROM borradores WHERE snapshot_id=? AND id=?",
                           (row["snapshot_id"], row["borrador_id"])).fetchone()
        if not row["texto"].strip() or row["texto"] not in draft[row["seccion"]]:
            raise ValueError("Afirmación no localizada en su sección del borrador")
    for row in db.execute("SELECT * FROM borradores"):
        questions = json.loads(row["preguntas_json"])
        if not isinstance(questions, list) or len(questions) != 3 or not all(isinstance(q, str) and q.strip() for q in questions):
            raise ValueError("Se requieren tres preguntas no vacías")
        if len(row["brief"].split()) > 250 or len(row["copy"].split()) > 80:
            raise ValueError("Borrador excede límite de palabras")
    for row in db.execute("SELECT * FROM priorizaciones"):
        components, weights = json.loads(row["componentes_json"]), json.loads(row["pesos_json"])
        if not isinstance(components, dict) or not isinstance(weights, dict) or set(components) != set("RIUNE") or set(weights) != set("RIUNE"):
            raise ValueError("Componentes/pesos deben ser R,I,U,N,E")
        if any(type(v) not in (int, float) or not math.isfinite(v)
               for v in list(components.values()) + list(weights.values())):
            raise ValueError("Pesos/componentes no numéricos o no finitos")
        if any(not 0 <= v <= 1 for v in components.values()) or any(v < 0 for v in weights.values()) or not math.isclose(sum(weights.values()), 100):
            raise ValueError("Rangos de pesos/componentes inválidos")
        if not math.isclose(sum(components[k] * weights[k] for k in components), row["puntaje"], abs_tol=1e-8):
            raise ValueError("Puntaje incoherente con componentes y pesos")
    for row in db.execute("SELECT * FROM noticias"):
        for field in ("fecha_publicacion", "fecha_deteccion"):
            if row[field] is not None and utc(row[field]) > utc(row["fecha_extraccion"]):
                raise ValueError("Fecha de noticia posterior a extracción")
    for row in db.execute("SELECT * FROM fuentes"):
        for table in ("noticias", "indicadores"):
            if row["familia"] != table and db.execute(
                f"SELECT 1 FROM {table} WHERE snapshot_id=? AND fuente_id=?",
                (row["snapshot_id"], row["id"])
            ).fetchone():
                raise ValueError("Familia de fuente incompatible")


def load_fixture(payload):
    """Solo fixtures sintéticos, no es el importador oficial por filas de T01."""
    if not isinstance(payload, dict) or payload.get("contract_version") != VERSION:
        raise ValueError("Versión de contrato incompatible")
    tables = payload.get("tables")
    if not isinstance(tables, dict) or set(tables) != set(TABLES):
        raise ValueError("Colecciones incompletas o desconocidas")
    if not isinstance(tables["snapshots"], list) or not tables["snapshots"]:
        raise ValueError("Se requiere snapshot sintético")
    if any(not isinstance(r, dict) or r.get("naturaleza") != "sintetico" for r in tables["snapshots"]):
        raise ValueError("El cargador demo solo admite fixtures sintéticos")
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    try:
        db.executescript((ROOT / "contracts/sqlite/schema.sql").read_text(encoding="utf-8"))
        with db:
            for table in TABLES:
                columns = {r["name"] for r in db.execute(f"PRAGMA table_info({table})")}
                rows = tables[table]
                if not isinstance(rows, list):
                    raise ValueError(f"{table}: se esperaba una lista")
                for row in rows:
                    if not isinstance(row, dict) or not row or not set(row) <= columns:
                        raise ValueError(f"{table}: campos desconocidos")
                    for key, value in row.items():
                        if isinstance(value, (dict, list, bool)):
                            raise ValueError("Campos escalares; JSON interno debe estar serializado")
                        if isinstance(value, float) and not math.isfinite(value):
                            raise ValueError("No se permiten NaN ni infinito")
                        if value is not None and key.startswith("fecha_"):
                            utc(value)
                        if value is not None and key in ("id", "snapshot_id") and (not isinstance(value, str) or not value.startswith("SYN-")):
                            raise ValueError("IDs del fixture requieren SYN-")
                        if value is not None and key in ("url", "fuente_url"):
                            parsed = urlsplit(value)
                            if parsed.scheme != "https" or parsed.hostname != "example.invalid":
                                raise ValueError("URLs del fixture deben ser https://example.invalid/...")
                    names = list(row)
                    placeholders = ",".join("?" for _ in names)
                    db.execute(f"INSERT INTO {table} ({','.join(names)}) VALUES ({placeholders})",
                               [row[n] for n in names])
            validate_relations(db)
            if db.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("Relaciones inválidas")
    except Exception:
        db.close()
        raise
    return db


def save_new(db, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb"):
        pass  # Creación exclusiva: nunca sobrescribir.
    target = sqlite3.connect(path)
    try:
        db.backup(target)
    finally:
        target.close()


def main():
    parser = argparse.ArgumentParser(description="Validar datos sintéticos contra el contrato.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path, help="Crear archivo SQLite nuevo; no sobrescribe")
    args = parser.parse_args()
    db = load_fixture(json.loads(args.fixture.read_text(encoding="utf-8")))
    try:
        if args.output:
            save_new(db, args.output)
        print(json.dumps({
            "contrato": VERSION, "naturaleza": "sintetico",
            "conteos": {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES},
            "procedencias": [dict(r) for r in db.execute("SELECT * FROM procedencias_grupos")],
            "base_creada": str(args.output) if args.output else None,
            "limite": "Integridad estructural; no demuestra IA, verdad ni T01-T10 completas."
        }, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()

