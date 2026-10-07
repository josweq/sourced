"""Interfaz local de lectura y revisión. Solo escucha en localhost."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
import time
import unicodedata
from urllib.parse import parse_qs, unquote, urlparse
import uuid

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent / "static"
STATES = {"en_revision", "requiere_evidencia", "aprobado_como_borrador", "descartado"}
EVIDENCE_STATES = {"insuficiente", "parcial", "suficiente_para_borrador"}
TOPICS = {"economia", "logistica_canal", "turismo", "servicios_publicos",
          "eventos_naturales", "regulacion", "sin_clasificar"}
SEARCH_STOPWORDS = {"a", "al", "con", "de", "del", "el", "en", "la", "las",
                    "los", "para", "por", "que", "se", "sin", "un", "una", "y"}


@contextmanager
def connect(path):
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
    finally:
        db.close()


def list_cases(db):
    rows = db.execute("""
      SELECT c.snapshot_id,c.id,c.titulo,c.estado_evidencia,c.preguntas_pendientes,
             ec.estado_revision,p.puntaje,p.componentes_json,p.reglas_version,
             COALESCE(pg.publicaciones,0) AS publicaciones,
             COALESCE(pg.procedencias_identificadas,0) AS procedencias_identificadas,
             COALESCE(pg.publicaciones_origen_desconocido,0) AS publicaciones_origen_desconocido
      FROM casos c JOIN estado_casos ec ON ec.snapshot_id=c.snapshot_id AND ec.id=c.id
      LEFT JOIN procedencias_grupos pg ON pg.snapshot_id=c.snapshot_id AND pg.grupo_id=c.grupo_id
      LEFT JOIN priorizaciones p ON p.rowid=(SELECT p2.rowid FROM priorizaciones p2
        WHERE p2.snapshot_id=c.snapshot_id AND p2.caso_id=c.id ORDER BY p2.fecha_utc DESC LIMIT 1)
      ORDER BY COALESCE(p.puntaje,-1) DESC,c.id
    """).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["componentes"] = json.loads(item.pop("componentes_json")) if item["componentes_json"] else None
        result.append(item)
    return result


def search_tokens(value):
    plain = unicodedata.normalize("NFKD", value.lower()).encode("ascii", "ignore").decode()
    return {part for part in re.findall(r"[a-z0-9]+", plain)
            if len(part) > 1 and part not in SEARCH_STOPWORDS}


def search_cases(db, query="", topic="", evidence_state="", medium="",
                 date_from="", date_to=""):
    started = time.perf_counter()
    if len(query) > 200 or len(medium) > 100:
        raise ValueError("Consulta o medio demasiado largo")
    if topic and topic not in TOPICS:
        raise ValueError("Tema inválido")
    if evidence_state and evidence_state not in EVIDENCE_STATES:
        raise ValueError("Estado de evidencia inválido")
    for label, value in (("date_from", date_from), ("date_to", date_to)):
        if value:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError(f"{label} debe usar una fecha válida YYYY-MM-DD") from exc
    if date_from and date_to and date_from > date_to:
        raise ValueError("La fecha inicial no puede ser posterior a la fecha final")
    wanted = search_tokens(query)
    results = []
    for case in list_cases(db):
        rows = db.execute("""SELECT n.titulo,n.medio,n.fecha_publicacion,g.tema
          FROM casos c JOIN grupos g ON g.snapshot_id=c.snapshot_id AND g.id=c.grupo_id
          JOIN grupo_noticias gn ON gn.snapshot_id=g.snapshot_id AND gn.grupo_id=g.id
          JOIN noticias n ON n.snapshot_id=gn.snapshot_id AND n.id=gn.noticia_id
          WHERE c.snapshot_id=? AND c.id=? ORDER BY n.id""",
          (case["snapshot_id"], case["id"])).fetchall()
        if not rows or (topic and rows[0]["tema"] != topic):
            continue
        if evidence_state and case["estado_evidencia"] != evidence_state:
            continue
        if medium and not any(medium.lower() in row["medio"].lower() for row in rows):
            continue
        if date_from or date_to:
            dated = [row["fecha_publicacion"][:10] for row in rows if row["fecha_publicacion"]]
            in_range = [value for value in dated
                        if (not date_from or value >= date_from)
                        and (not date_to or value <= date_to)]
            if not in_range:
                continue
        corpus = search_tokens(" ".join(row["titulo"] for row in rows))
        matches = sorted(wanted & corpus)
        if wanted and not matches:
            continue
        lexical = len(matches) / len(wanted) if wanted else 0.0
        item = dict(case)
        item.update({"tema": rows[0]["tema"], "medios": sorted({row["medio"] for row in rows}),
                     "coincidencias": matches, "relevancia_textual": round(lexical, 3),
                     "motivo": ("Coincidencias: " + ", ".join(matches)) if matches else "Coincide con los filtros seleccionados."})
        results.append(item)
    results.sort(key=lambda item: (-item["relevancia_textual"],
                                   -(item["puntaje"] if item["puntaje"] is not None else -1), item["id"]))
    return {"consulta": query, "filtros": {"tema": topic, "evidencia": evidence_state,
            "medio": medium, "desde": date_from, "hasta": date_to},
            "resultados": results, "abstencion": not results,
            "motivo_abstencion": "No hay casos sustentados que coincidan con la consulta y los filtros." if not results else None,
            "tiempo_ms": round((time.perf_counter() - started) * 1000, 3),
            "baseline": "palabras-clave-v1"}


def case_detail(db, case_id):
    case = db.execute("""SELECT c.*,ec.estado_revision FROM casos c
      JOIN estado_casos ec ON ec.snapshot_id=c.snapshot_id AND ec.id=c.id WHERE c.id=?""",
      (case_id,)).fetchone()
    if not case:
        return None
    snapshot_id = case["snapshot_id"]
    grouping = db.execute("""SELECT publicaciones,procedencias_identificadas,
      publicaciones_origen_desconocido FROM procedencias_grupos
      WHERE snapshot_id=? AND grupo_id=?""", (snapshot_id, case["grupo_id"])).fetchone() if case["grupo_id"] else None
    priority = db.execute("""SELECT puntaje,componentes_json,pesos_json,reglas_version,explicacion,fecha_utc
      FROM priorizaciones WHERE snapshot_id=? AND caso_id=? ORDER BY fecha_utc DESC LIMIT 1""",
      (snapshot_id, case_id)).fetchone()
    evidence = [dict(r) for r in db.execute("""SELECT e.id,e.campo,e.limitaciones,
      n.titulo AS noticia_titulo,n.url AS noticia_url,n.fecha_publicacion,n.fecha_deteccion,n.alcance_texto,
      i.pais_iso3,i.indicador_id,i.anio,i.valor,i.unidad,i.fuente_url
      FROM caso_evidencias ce JOIN evidencias e ON e.snapshot_id=ce.snapshot_id AND e.id=ce.evidencia_id
      LEFT JOIN noticias n ON n.snapshot_id=e.snapshot_id AND n.id=e.noticia_id
      LEFT JOIN indicadores i ON i.snapshot_id=e.snapshot_id AND i.id=e.indicador_registro_id
      WHERE ce.snapshot_id=? AND ce.caso_id=? ORDER BY e.id""", (snapshot_id, case_id))]
    drafts = [dict(r) for r in db.execute("""SELECT id,version,titulo,enfoque,brief,guion,copy,
      preguntas_json,alcance_texto,generador,modelo_version,prompt_version,fecha_utc
      FROM borradores WHERE snapshot_id=? AND caso_id=? ORDER BY version DESC""", (snapshot_id, case_id))]
    for draft in drafts:
        draft["preguntas"] = json.loads(draft.pop("preguntas_json"))
        draft["afirmaciones"] = [dict(r) for r in db.execute("""SELECT a.id,a.seccion,a.texto,a.tipo,
          c.evidencia_id,c.relacion,c.explicacion FROM afirmaciones a
          LEFT JOIN citas c ON c.snapshot_id=a.snapshot_id AND c.afirmacion_id=a.id
          WHERE a.snapshot_id=? AND a.borrador_id=? ORDER BY a.id,c.evidencia_id""", (snapshot_id, draft["id"]))]
    reviews = [dict(r) for r in db.execute("""SELECT secuencia,persona_revisora,estado,comentario,fecha_utc,borrador_id
      FROM revisiones WHERE snapshot_id=? AND caso_id=? ORDER BY secuencia DESC""", (snapshot_id, case_id))]
    priority_data = dict(priority) if priority else None
    if priority_data:
        priority_data["componentes"] = json.loads(priority_data.pop("componentes_json"))
        priority_data["pesos"] = json.loads(priority_data.pop("pesos_json"))
        priority_data["explicacion"] = json.loads(priority_data["explicacion"])
    return {"caso": dict(case), "agrupacion": dict(grouping) if grouping else None,
            "priorizacion": priority_data, "evidencias": evidence,
            "borradores": drafts, "revisiones": reviews}


def add_review(db, case_id, payload):
    reviewer = str(payload.get("persona_revisora", "")).strip()
    state = payload.get("estado")
    comment = str(payload.get("comentario", "")).strip()
    draft_id = payload.get("borrador_id") or None
    if not 2 <= len(reviewer) <= 80:
        raise ValueError("La persona revisora debe tener entre 2 y 80 caracteres")
    if state not in STATES:
        raise ValueError("Estado de revisión inválido")
    if not 3 <= len(comment) <= 1000:
        raise ValueError("El comentario debe tener entre 3 y 1000 caracteres")
    row = db.execute("SELECT snapshot_id FROM casos WHERE id=?", (case_id,)).fetchone()
    if not row:
        raise LookupError("Caso no encontrado")
    snapshot_id = row["snapshot_id"]
    if draft_id and not db.execute("SELECT 1 FROM borradores WHERE snapshot_id=? AND caso_id=? AND id=?",
                                   (snapshot_id, case_id, draft_id)).fetchone():
        raise ValueError("El borrador no pertenece al caso")
    if state == "aprobado_como_borrador" and not draft_id:
        raise ValueError("Para aprobar se debe seleccionar un borrador")
    sequence = db.execute("SELECT COALESCE(MAX(secuencia),0)+1 FROM revisiones WHERE snapshot_id=? AND caso_id=?",
                          (snapshot_id, case_id)).fetchone()[0]
    review_id = "REV-" + uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    with db:
        db.execute("INSERT INTO revisiones VALUES (?,?,?,?,?,?,?,?,?)",
                   (snapshot_id, review_id, case_id, draft_id, sequence, reviewer, state, comment, now))
    return {"id": review_id, "secuencia": sequence, "fecha_utc": now}


class Handler(BaseHTTPRequestHandler):
    db_path = None

    def security_headers(self, content_type):
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:")

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.security_headers("application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path
        if route in ("/", "/index.html"):
            return self.send_file("index.html", "text/html; charset=utf-8")
        if route == "/styles.css":
            return self.send_file("styles.css", "text/css; charset=utf-8")
        if route == "/app.js":
            return self.send_file("app.js", "text/javascript; charset=utf-8")
        try:
            with connect(self.db_path) as db:
                if route == "/api/cases":
                    return self.send_json(200, {"casos": list_cases(db), "modo": "local"})
                if route == "/api/search":
                    params = parse_qs(parsed.query, keep_blank_values=True)
                    get = lambda name: params.get(name, [""])[0].strip()
                    try:
                        return self.send_json(200, search_cases(db, get("q"), get("tema"),
                                              get("evidencia"), get("medio"), get("desde"), get("hasta")))
                    except ValueError as exc:
                        return self.send_json(400, {"error": str(exc)})
                match = re.fullmatch(r"/api/cases/([^/]+)", route)
                if match:
                    detail = case_detail(db, unquote(match.group(1)))
                    return self.send_json(200, detail) if detail else self.send_json(404, {"error": "Caso no encontrado"})
        except sqlite3.Error:
            return self.send_json(500, {"error": "No se pudo consultar la base local"})
        self.send_json(404, {"error": "Ruta no encontrada"})

    def do_POST(self):
        route = urlparse(self.path).path
        match = re.fullmatch(r"/api/cases/([^/]+)/reviews", route)
        if not match:
            return self.send_json(404, {"error": "Ruta no encontrada"})
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}:
            return self.send_json(403, {"error": "Origen no permitido"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 8192:
                raise ValueError("Cuerpo inválido o demasiado grande")
            payload = json.loads(self.rfile.read(length))
            with connect(self.db_path) as db:
                result = add_review(db, unquote(match.group(1)), payload)
            self.send_json(201, result)
        except json.JSONDecodeError:
            self.send_json(400, {"error": "JSON inválido"})
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
        except LookupError as exc:
            self.send_json(404, {"error": str(exc)})
        except sqlite3.Error:
            self.send_json(409, {"error": "No se pudo registrar la revisión"})

    def send_file(self, name, content_type):
        body = (STATIC / name).read_bytes()
        self.send_response(200)
        self.security_headers(content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def main():
    parser = argparse.ArgumentParser(description="Interfaz editorial local")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not args.db.is_file():
        raise SystemExit(f"Base no encontrada: {args.db}")
    Handler.db_path = args.db.resolve()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Jajanken Lupa: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
