"""Importa noticias.csv e indicadores.csv por fila y genera cuarentena reproducible."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit

try:
    from scripts.modelo_datos import ROOT, save_new, utc
except ModuleNotFoundError:  # Permite `python scripts/importar_csv.py` desde la raíz.
    from modelo_datos import ROOT, save_new, utc

NEWS_FIELDS = (
    "id_noticia", "titulo", "url", "medio", "idioma", "fecha_publicacion",
    "fecha_deteccion", "fecha_extraccion", "tema", "origen", "alcance_texto",
)
INDICATOR_FIELDS = (
    "pais_iso3", "indicador_id", "anio", "valor", "unidad", "fuente_url",
    "fecha_extraccion", "licencia",
)
TOPICS = {"economia", "logistica_canal", "turismo", "servicios_publicos",
          "eventos_naturales", "regulacion", "sin_clasificar"}
SCOPES = {"titular_metadatos", "extracto_autorizado", "texto_autorizado"}


def required_headers(path, expected):
    stream = path.open("r", encoding="utf-8-sig", newline="")
    reader = csv.DictReader(stream)
    actual = tuple(reader.fieldnames or ())
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    if missing or extra:
        stream.close()
        raise ValueError(f"{path.name}: encabezados inválidos; faltan={missing}, sobran={extra}")
    return stream, reader


def clean(value):
    return value.strip() if isinstance(value, str) else value


def valid_https(value, field):
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"{field} debe ser URL HTTPS")
    return value


def parse_optional_utc(value, field):
    if not value:
        return None
    try:
        utc(value)
    except ValueError as exc:
        raise ValueError(f"{field}: {exc}") from exc
    return value


def indicator_pk(row):
    raw = "|".join((row["pais_iso3"], row["indicador_id"], str(row["anio"])))
    return "IND-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def normalize_news(raw):
    row = {key: clean(raw[key]) for key in NEWS_FIELDS}
    for field in ("id_noticia", "titulo", "medio", "idioma", "fecha_extraccion"):
        if not row[field]:
            raise ValueError(f"{field} es obligatorio")
    valid_https(row["url"], "url")
    row["fecha_publicacion"] = parse_optional_utc(row["fecha_publicacion"], "fecha_publicacion")
    row["fecha_deteccion"] = parse_optional_utc(row["fecha_deteccion"], "fecha_deteccion")
    utc(row["fecha_extraccion"])
    extracted = utc(row["fecha_extraccion"])
    for field in ("fecha_publicacion", "fecha_deteccion"):
        if row[field] and utc(row[field]) > extracted:
            raise ValueError(f"{field} no puede ser posterior a fecha_extraccion")
    if row["tema"] not in TOPICS:
        raise ValueError("tema fuera del catálogo")
    if row["alcance_texto"] not in SCOPES:
        raise ValueError("alcance_texto fuera del catálogo")
    row["origen"] = row["origen"] or None
    return row


def normalize_indicator(raw):
    row = {key: clean(raw[key]) for key in INDICATOR_FIELDS}
    for field in ("pais_iso3", "indicador_id", "anio", "unidad", "fuente_url",
                  "fecha_extraccion", "licencia"):
        if not row[field]:
            raise ValueError(f"{field} es obligatorio")
    row["pais_iso3"] = row["pais_iso3"].upper()
    if len(row["pais_iso3"]) != 3 or not row["pais_iso3"].isalpha():
        raise ValueError("pais_iso3 debe tener tres letras")
    try:
        row["anio"] = int(row["anio"])
    except ValueError as exc:
        raise ValueError("anio debe ser entero") from exc
    if not 1900 <= row["anio"] <= 2100:
        raise ValueError("anio fuera de rango razonable")
    if row["valor"] == "":
        row["valor"] = None
    else:
        try:
            row["valor"] = float(row["valor"])
        except ValueError as exc:
            raise ValueError("valor debe ser numérico o vacío") from exc
    valid_https(row["fuente_url"], "fuente_url")
    utc(row["fecha_extraccion"])
    return row


def import_rows(db, path, expected, normalizer, inserter, kind):
    accepted, errors = 0, []
    stream, reader = required_headers(path, expected)
    try:
        for line, raw in enumerate(reader, start=2):
            try:
                row = normalizer(raw)
                with db:
                    inserter(db, row)
                accepted += 1
            except (ValueError, sqlite3.IntegrityError) as exc:
                errors.append({"archivo": path.name, "fila": line, "tipo": kind,
                               "id": raw.get("id_noticia") or raw.get("indicador_id"),
                               "error": str(exc)})
    finally:
        stream.close()
    return accepted, errors


def load_sources(path, extracted):
    if path is None:
        return [
            ("SRC-NOTICIAS", "Noticias CSV", "noticias", "https://example.invalid/receta-noticias", "Sustituir por catálogo oficial al recibirlo", extracted),
            ("SRC-INDICADORES", "Indicadores CSV", "indicadores", "https://example.invalid/receta-indicadores", "Sustituir por catálogo oficial al recibirlo", extracted),
        ]
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("fuentes.json debe contener una lista")
    sources = []
    for item in payload:
        row = {key: clean(item.get(key, "")) for key in
               ("id", "nombre", "familia", "url", "condiciones", "fecha_extraccion")}
        for field, value in row.items():
            if not value:
                raise ValueError(f"fuentes.json: {field} es obligatorio")
        if row["familia"] not in {"noticias", "indicadores"}:
            raise ValueError("fuentes.json: familia inválida")
        valid_https(row["url"], "url")
        utc(row["fecha_extraccion"])
        sources.append((row["id"], row["nombre"], row["familia"], row["url"],
                        row["condiciones"], row["fecha_extraccion"]))
    if not any(row[2] == "noticias" for row in sources) or not any(row[2] == "indicadores" for row in sources):
        raise ValueError("fuentes.json debe incluir familias noticias e indicadores")
    return sources


def run_import(news_path, indicators_path, output, report_path, snapshot_id,
               version, cutoff, fuentes_path=None):
    if output.exists() or report_path.exists():
        raise FileExistsError("La base o el reporte ya existe; no se sobrescribe")
    utc(cutoff)
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript((ROOT / "contracts/sqlite/schema.sql").read_text(encoding="utf-8"))
    db.execute("INSERT INTO snapshots VALUES (?,?,?,?,?)",
               (snapshot_id, version, "real", cutoff, "Importación CSV local"))
    extracted = cutoff
    source_rows = load_sources(fuentes_path, extracted)
    db.executemany("INSERT INTO fuentes VALUES (?,?,?,?,?,?,?)",
                   [(snapshot_id, *row) for row in source_rows])
    news_source = next(row[0] for row in source_rows if row[2] == "noticias")
    # Cada noticia apunta a la fuente de su medio («La Prensa» → «La Prensa (RSS)»), no a la primera del catálogo.
    news_source_by_medio = {}
    for row in source_rows:
        if row[2] == "noticias":
            news_source_by_medio.setdefault(row[1].split(" (")[0].strip().casefold(), row[0])
    indicator_source = next(row[0] for row in source_rows if row[2] == "indicadores")
    db.commit()  # Una fila rechazada no debe revertir el snapshot ni su catálogo.

    def insert_news(conn, row):
        conn.execute("""INSERT INTO noticias
          (snapshot_id,id,fuente_id,titulo,url,medio,idioma,fecha_publicacion,
           fecha_deteccion,fecha_extraccion,tema,origen,alcance_texto,texto_disponible)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)""",
          (snapshot_id, row["id_noticia"],
           news_source_by_medio.get(row["medio"].strip().casefold(), news_source),
           row["titulo"], row["url"],
           row["medio"], row["idioma"], row["fecha_publicacion"], row["fecha_deteccion"],
           row["fecha_extraccion"], row["tema"], row["origen"], row["alcance_texto"]))

    def insert_indicator(conn, row):
        conn.execute("""INSERT INTO indicadores
          (snapshot_id,id,fuente_id,pais_iso3,indicador_id,anio,valor,unidad,
           fuente_url,fecha_extraccion,licencia) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
          (snapshot_id, indicator_pk(row), indicator_source, row["pais_iso3"],
           row["indicador_id"], row["anio"], row["valor"], row["unidad"],
           row["fuente_url"], row["fecha_extraccion"], row["licencia"]))

    news_ok, news_errors = import_rows(db, news_path, NEWS_FIELDS, normalize_news,
                                       insert_news, "noticia")
    ind_ok, ind_errors = import_rows(db, indicators_path, INDICATOR_FIELDS,
                                     normalize_indicator, insert_indicator, "indicador")
    errors = news_errors + ind_errors
    report = {
        "snapshot_id": snapshot_id, "version": version, "fecha_corte_utc": cutoff,
        "archivos": {
            news_path.name: {"aceptadas": news_ok, "rechazadas": len(news_errors)},
            indicators_path.name: {"aceptadas": ind_ok, "rechazadas": len(ind_errors)},
        },
        "errores": errors,
        "advertencias": [
            "No se aplicó el filtro temporal ambiguo del PDF.",
            "Las fuentes temporales example.invalid deben reemplazarse con fuentes.json oficial." if fuentes_path is None else "Catálogo fuentes.json cargado.",
        ],
    }
    save_new(db, output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    db.close()
    return report


def main():
    parser = argparse.ArgumentParser(description="Importar CSV por fila con reporte de cuarentena")
    parser.add_argument("--noticias", type=Path, required=True)
    parser.add_argument("--indicadores", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--fecha-corte-utc", required=True)
    parser.add_argument("--fuentes", type=Path)
    args = parser.parse_args()
    print(json.dumps(run_import(args.noticias, args.indicadores, args.output,
                                args.report, args.snapshot_id, args.version,
                                args.fecha_corte_utc, args.fuentes), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
