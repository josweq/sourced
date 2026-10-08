"""Interfaz local de lectura y revisión. Solo escucha en localhost."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from pathlib import Path
import re
import sqlite3
import time
import unicodedata
from urllib.parse import parse_qs, unquote, urlparse
import uuid

import sys

# Permite `python src/interfaz/app.py` desde la raíz (el comando del README), no solo `python -m`.
if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.editorial.cronometro import resumen_cronometro  # noqa: E402
from src.ia.proveedores import ProviderUnavailable, estado_proveedor, modelo_activo, proveedor_activo
from src.ia.redaccion import cargar_evidencias_caso, generar_paquete, guardar_borrador

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent / "static"
STATIC_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
}
STATIC_ROOT_FILES = {"index.html", "styles.css", "tokens.css", "app.js", "favicon.svg"}
STATIC_DIRS = {"fonts", "img"}
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


def snapshot_metadata(db):
    row = db.execute("""SELECT id,version,fecha_corte_utc,descripcion
      FROM snapshots ORDER BY fecha_corte_utc DESC LIMIT 1""").fetchone()
    return dict(row) if row else None


def estado_local(db):
    snapshot = snapshot_metadata(db)
    provider = estado_proveedor()
    return {"snapshot": snapshot, "corte": snapshot["fecha_corte_utc"] if snapshot else None,
            "modelo": {"proveedor": proveedor_activo(), "nombre": modelo_activo(),
                       "ollama_responde": provider["disponible"], "motivo": provider["motivo"]}}


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
        rows = db.execute("""SELECT n.titulo,n.medio,n.fecha_publicacion,n.fecha_deteccion,g.tema
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
        first_publication = next((row["fecha_publicacion"] for row in rows if row["fecha_publicacion"]), None)
        first_detection = next((row["fecha_deteccion"] for row in rows if row["fecha_deteccion"]), None)
        item.update({"tema": rows[0]["tema"], "medios": sorted({row["medio"] for row in rows}),
                     "fecha_publicacion": first_publication, "fecha_deteccion": first_detection,
                     "coincidencias": matches, "relevancia_textual": round(lexical, 3),
                     "motivo": ("Coincidencias: " + ", ".join(matches)) if matches else ""})
        results.append(item)
    results.sort(key=lambda item: (-item["relevancia_textual"],
                                   -(item["puntaje"] if item["puntaje"] is not None else -1), item["id"]))
    return {"consulta": query, "filtros": {"tema": topic, "evidencia": evidence_state,
            "medio": medium, "desde": date_from, "hasta": date_to},
            "resultados": results, "abstencion": not results,
            "motivo_abstencion": "No hay casos sustentados que coincidan con la consulta y los filtros." if not results else None,
            "tiempo_ms": round((time.perf_counter() - started) * 1000, 3),
            "baseline": "palabras-clave-v1", "snapshot": snapshot_metadata(db)}


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
      n.id AS noticia_id,n.titulo AS noticia_titulo,n.url AS noticia_url,n.medio,
      n.fecha_publicacion,n.fecha_deteccion,n.alcance_texto,
      fn.nombre AS fuente_nombre,gn.procedencia_id,gn.justificacion_procedencia,
      i.pais_iso3,i.indicador_id,i.anio,i.valor,i.unidad,i.fuente_url,fi.nombre AS indicador_fuente_nombre
      FROM caso_evidencias ce JOIN evidencias e ON e.snapshot_id=ce.snapshot_id AND e.id=ce.evidencia_id
      LEFT JOIN noticias n ON n.snapshot_id=e.snapshot_id AND n.id=e.noticia_id
      LEFT JOIN fuentes fn ON fn.snapshot_id=n.snapshot_id AND fn.id=n.fuente_id
      LEFT JOIN casos c ON c.snapshot_id=ce.snapshot_id AND c.id=ce.caso_id
      LEFT JOIN grupo_noticias gn ON gn.snapshot_id=e.snapshot_id AND gn.grupo_id=c.grupo_id AND gn.noticia_id=n.id
      LEFT JOIN indicadores i ON i.snapshot_id=e.snapshot_id AND i.id=e.indicador_registro_id
      LEFT JOIN fuentes fi ON fi.snapshot_id=i.snapshot_id AND fi.id=i.fuente_id
      WHERE ce.snapshot_id=? AND ce.caso_id=? ORDER BY e.id""", (snapshot_id, case_id))]
    drafts = [dict(r) for r in db.execute("""SELECT id,version,titulo,enfoque,brief,guion,copy,
      preguntas_json,alcance_texto,generador,modelo_version,prompt_version,fecha_utc
      FROM borradores WHERE snapshot_id=? AND caso_id=? ORDER BY version DESC""", (snapshot_id, case_id))]
    for draft in drafts:
        draft["preguntas"] = json.loads(draft.pop("preguntas_json"))
        draft["meta"] = parse_draft_meta(draft.get("prompt_version"))
        draft["cronometro"] = resumen_cronometro(draft["guion"])
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
            "borradores": drafts, "revisiones": reviews, "snapshot": snapshot_metadata(db)}


def parse_draft_meta(prompt_version):
    value = prompt_version or ""
    if " {" not in value:
        return {"prompt_version": value}
    version, raw = value.split(" ", 1)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {}
    parsed["prompt_version"] = version
    return parsed


def latest_draft(db, case_id):
    detail = case_detail(db, case_id)
    if not detail:
        return None
    return {"caso": detail["caso"], "evidencias": detail["evidencias"],
            "borrador": detail["borradores"][0] if detail["borradores"] else None,
            "versiones": detail["borradores"], "snapshot": detail["snapshot"]}


def regenerate_draft(db, case_id, proveedor=None):
    proveedor = proveedor or generar_paquete
    case, evidences = cargar_evidencias_caso(db, case_id)
    package = proveedor(case, evidences)
    if package.get("estado") == "abstencion" and not package.get("afirmaciones"):
        return {"estado": "abstencion", "explicacion": package.get("explicacion"), "retiradas": package.get("retiradas", [])}
    saved = guardar_borrador(db, case_id, package, "modelo")
    return {"estado": package.get("estado"), "borrador": saved, "guardian": package.get("guardian"),
            "cronometro": package.get("cronometro")}


def save_human_version(db, draft_id, payload):
    row = db.execute("SELECT * FROM borradores WHERE id=?", (draft_id,)).fetchone()
    if not row:
        raise LookupError("Borrador no encontrado")
    allowed = {key: str(payload.get(key, row[key]) or "") for key in ("titulo", "enfoque", "brief", "guion", "copy")}
    preguntas = payload.get("preguntas")
    if preguntas is None:
        preguntas = json.loads(row["preguntas_json"])
    if not isinstance(preguntas, list):
        raise ValueError("preguntas debe ser una lista")
    version = db.execute("SELECT COALESCE(MAX(version),0)+1 FROM borradores WHERE snapshot_id=? AND caso_id=?",
                         (row["snapshot_id"], row["caso_id"])).fetchone()[0]
    new_id = "BOR-" + uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    with db:
        db.execute("""INSERT INTO borradores VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (row["snapshot_id"], new_id, row["caso_id"], version, allowed["titulo"],
                    allowed["enfoque"], allowed["brief"], allowed["guion"], allowed["copy"],
                    json.dumps(preguntas[:3], ensure_ascii=False), row["alcance_texto"], "humano",
                    row["modelo_version"], row["prompt_version"], now))
        original_claims = db.execute("""SELECT a.*,c.evidencia_id FROM afirmaciones a
          JOIN citas c ON c.snapshot_id=a.snapshot_id AND c.caso_id=a.caso_id AND c.afirmacion_id=a.id
          WHERE a.snapshot_id=? AND a.borrador_id=? ORDER BY a.id""",
          (row["snapshot_id"], row["id"])).fetchall()
        for index, claim in enumerate(original_claims, 1):
            section_text = allowed.get(claim["seccion"], "")
            changed = claim["texto"] not in section_text
            claim_id = f"AF-{new_id}-{index}"
            db.execute("INSERT INTO afirmaciones VALUES (?,?,?,?,?,?,?)",
                       (row["snapshot_id"], claim_id, row["caso_id"], new_id, claim["seccion"],
                        claim["texto"], claim["tipo"]))
            explanation = "revisar: la edicion humana modifico la oracion citada." if changed else "Cita heredada sin cambios."
            db.execute("INSERT INTO citas VALUES (?,?,?,?,?,?)",
                       (row["snapshot_id"], row["caso_id"], claim_id, claim["evidencia_id"], "sustenta", explanation))
    return {"id": new_id, "version": version, "fecha_utc": now}


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
    if state == "aprobado_como_borrador":
        blocked = db.execute("""SELECT 1 FROM citas WHERE snapshot_id=? AND caso_id=?
          AND afirmacion_id IN (SELECT id FROM afirmaciones WHERE snapshot_id=? AND borrador_id=?)
          AND (lower(explicacion) LIKE '%revisar%' OR lower(explicacion) LIKE '%sin fuente%') LIMIT 1""",
          (snapshot_id, case_id, snapshot_id, draft_id)).fetchone()
        if blocked:
            raise ValueError("No se puede aprobar con citas marcadas revisar o sin fuente")
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
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; font-src 'self'")

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
        if route == "/":
            return self.send_static("index.html")
        if route.startswith(("/api/", "/api?")):
            pass
        elif self.is_static_route(route):
            return self.send_static(route.lstrip("/"))
        try:
            with connect(self.db_path) as db:
                if route == "/api/cases":
                    return self.send_json(200, {"casos": list_cases(db), "modo": "local",
                                                "snapshot": snapshot_metadata(db)})
                if route == "/api/estado":
                    return self.send_json(200, estado_local(db))
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
                match = re.fullmatch(r"/api/cases/([^/]+)/borrador", route)
                if match:
                    draft = latest_draft(db, unquote(match.group(1)))
                    return self.send_json(200, draft) if draft else self.send_json(404, {"error": "Caso no encontrado"})
        except sqlite3.Error:
            return self.send_json(500, {"error": "No se pudo consultar la base local"})
        self.send_json(404, {"error": "Ruta no encontrada"})

    def do_POST(self):
        route = urlparse(self.path).path
        match_review = re.fullmatch(r"/api/cases/([^/]+)/reviews", route)
        match_draft = re.fullmatch(r"/api/cases/([^/]+)/borrador", route)
        is_query = route == "/api/consulta"
        if not match_review and not match_draft and not is_query:
            return self.send_json(404, {"error": "Ruta no encontrada"})
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}:
            return self.send_json(403, {"error": "Origen no permitido"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 8192:
                raise ValueError("Cuerpo inválido o demasiado grande")
            payload = json.loads(self.rfile.read(length)) if length else {}
            if is_query:
                from src.ia.consulta import responder  # carga diferida: el modelo pesa
                with connect(self.db_path) as db:
                    return self.send_json(200, responder(db, str(payload.get("pregunta", ""))))
            with connect(self.db_path) as db:
                if match_draft:
                    provider = estado_proveedor()
                    if not provider["disponible"]:
                        return self.send_json(503, {"error": provider["motivo"], "modelo": provider})
                    result = regenerate_draft(db, unquote(match_draft.group(1)))
                else:
                    result = add_review(db, unquote(match_review.group(1)), payload)
            self.send_json(201, result)
        except UnicodeDecodeError:
            self.send_json(400, {"error": "El texto debe enviarse en UTF-8"})
        except json.JSONDecodeError:
            self.send_json(400, {"error": "JSON inválido"})
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
        except LookupError as exc:
            self.send_json(404, {"error": str(exc)})
        except ProviderUnavailable as exc:
            self.send_json(503, {"error": str(exc)})
        except sqlite3.Error:
            self.send_json(409, {"error": "No se pudo registrar la revisión"})

    def do_PUT(self):
        route = urlparse(self.path).path
        match = re.fullmatch(r"/api/borradores/([^/]+)", route)
        if not match:
            return self.send_json(404, {"error": "Ruta no encontrada"})
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}:
            return self.send_json(403, {"error": "Origen no permitido"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 65536:
                raise ValueError("Cuerpo inválido o demasiado grande")
            payload = json.loads(self.rfile.read(length))
            with connect(self.db_path) as db:
                result = save_human_version(db, unquote(match.group(1)), payload)
            self.send_json(201, result)
        except json.JSONDecodeError:
            self.send_json(400, {"error": "JSON inválido"})
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
        except LookupError as exc:
            self.send_json(404, {"error": str(exc)})
        except sqlite3.Error:
            self.send_json(409, {"error": "No se pudo guardar la version humana"})

    def is_static_route(self, route):
        name = unquote(route.lstrip("/"))
        if not name or "\\" in name or ".." in Path(name).parts:
            return False
        path = Path(name)
        if len(path.parts) == 1:
            return path.name in STATIC_ROOT_FILES
        return len(path.parts) == 2 and path.parts[0] in STATIC_DIRS and path.suffix in STATIC_TYPES

    def send_static(self, name):
        clean = unquote(name)
        if clean == "favicon.svg":
            clean = "img/lupa.svg"
        if "\\" in clean or ".." in Path(clean).parts:
            return self.send_json(404, {"error": "Ruta no encontrada"})
        path = STATIC / clean
        if path.suffix not in STATIC_TYPES or not path.is_file() or STATIC not in path.resolve().parents:
            return self.send_json(404, {"error": "Ruta no encontrada"})
        body = path.read_bytes()
        self.send_response(200)
        self.security_headers(STATIC_TYPES[path.suffix])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def calentar_modelo(db_path):
    """Precarga el modelo y el caché de titulares para que la primera pregunta no tarde un minuto."""
    try:
        from src.ia.consulta import responder
        with connect(db_path) as db:
            responder(db, "calentamiento del modelo local")
        print("Modelo de embeddings listo.")
    except Exception as exc:  # noqa: BLE001 - la interfaz sigue funcionando sin consultas
        print(f"No se pudo precargar el modelo de embeddings: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Interfaz editorial local")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--sin-calentar", action="store_true", help="No precarga el modelo de embeddings al arrancar.")
    args = parser.parse_args()
    if not args.db.is_file():
        raise SystemExit(f"Base no encontrada: {args.db}")
    Handler.db_path = args.db.resolve()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    if not args.sin_calentar:
        threading.Thread(target=calentar_modelo, args=(Handler.db_path,), daemon=True).start()
    print(f"Jajanken Lupa: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
