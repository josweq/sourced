"""Interfaz local de lectura y revisión. Solo escucha en localhost."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import unquote, urlparse
import uuid

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent / "static"
STATES = {"en_revision", "requiere_evidencia", "aprobado_como_borrador", "descartado"}


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
             ec.estado_revision,p.puntaje,p.componentes_json,p.reglas_version
      FROM casos c JOIN estado_casos ec ON ec.snapshot_id=c.snapshot_id AND ec.id=c.id
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


def case_detail(db, case_id):
    case = db.execute("""SELECT c.*,ec.estado_revision FROM casos c
      JOIN estado_casos ec ON ec.snapshot_id=c.snapshot_id AND ec.id=c.id WHERE c.id=?""",
      (case_id,)).fetchone()
    if not case:
        return None
    snapshot_id = case["snapshot_id"]
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
    return {"caso": dict(case), "evidencias": evidence, "borradores": drafts, "revisiones": reviews}


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
        route = urlparse(self.path).path
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
