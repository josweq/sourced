"""Baseline explicable: agrupa títulos, crea casos y calcula prioridad."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import unicodedata

try:
    from scripts.modelo_datos import save_new, utc, validate_relations
except ModuleNotFoundError:
    from modelo_datos import save_new, utc, validate_relations

RULES_VERSION = "baseline-titulos-v1"
WEIGHTS = {"R": 30, "I": 25, "U": 20, "N": 15, "E": 10}
IMPACT = {"economia": .70, "logistica_canal": .70, "turismo": .55,
          "servicios_publicos": .65, "eventos_naturales": .65,
          "regulacion": .65, "sin_clasificar": .30}
STOPWORDS = {"a", "al", "con", "de", "del", "el", "en", "la", "las", "los",
             "para", "por", "se", "sin", "un", "una", "y", "sintetico"}


def stable_id(prefix, values):
    digest = hashlib.sha256("|".join(sorted(values)).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}-{digest}"


def tokens(title):
    plain = unicodedata.normalize("NFKD", title.lower()).encode("ascii", "ignore").decode()
    return {part for part in re.findall(r"[a-z0-9]+", plain) if part not in STOPWORDS and len(part) > 1}


def similarity(left, right):
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def group_news(rows, threshold=.55):
    """Greedy, deterministic baseline within each topic; no claim of truth."""
    groups = []
    for row in sorted(rows, key=lambda item: item["id"]):
        row_tokens = tokens(row["titulo"])
        best, best_score = None, -1.0
        for group in groups:
            if group[0]["tema"] != row["tema"]:
                continue
            score = similarity(tokens(group[0]["titulo"]), row_tokens)
            if score >= threshold and score > best_score:
                best, best_score = group, score
        if best is None:
            groups.append([row])
        else:
            best.append(row)
    return groups


def urgency(latest, cutoff):
    if not latest:
        return .20, "Sin fecha de publicación: urgencia conservadora 0.20."
    age = max(0, (utc(cutoff) - utc(latest)).total_seconds() / 86400)
    if age <= 1:
        return 1.0, "Publicación dentro de 24 horas del corte."
    if age <= 3:
        return .75, "Publicación dentro de 72 horas del corte."
    if age <= 7:
        return .50, "Publicación dentro de siete días del corte."
    if age <= 30:
        return .25, "Publicación dentro de 30 días del corte."
    return .10, "Publicación anterior a 30 días del corte."


def ranking(group, cutoff):
    theme = Counter(row["tema"] for row in group).most_common(1)[0][0]
    known = len({row["origen"].strip().lower() for row in group if row["origen"]})
    latest = max((row["fecha_publicacion"] for row in group if row["fecha_publicacion"]), default=None)
    u, urgency_reason = urgency(latest, cutoff)
    components = {
        "R": .60 if theme != "sin_clasificar" else .20,
        "I": IMPACT[theme],
        "U": u,
        "N": .50,
        "E": min(.75, .25 + .25 * known),
    }
    score = round(sum(components[key] * WEIGHTS[key] for key in WEIGHTS), 2)
    explanation = {
        "R": "Tema de la modalidad editorial; relación geográfica con Panamá pendiente.",
        "I": f"Valor inicial documentado para la categoría {theme}; requiere revisión editorial.",
        "U": urgency_reason,
        "N": "0.50 fijo hasta contar con historial; duplicados no incrementan novedad.",
        "E": f"Solo titular/metadatos; {known} procedencia(s) identificada(s). Tope 0.75.",
    }
    return theme, components, score, explanation, known


def process(input_path, output_path, threshold=.55):
    if output_path.exists():
        raise FileExistsError("La salida ya existe; no se sobrescribe")
    source = sqlite3.connect(input_path)
    source.row_factory = sqlite3.Row
    try:
        existing = sum(source.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                       for table in ("grupos", "casos", "evidencias", "priorizaciones"))
        if existing:
            raise ValueError("La entrada ya contiene datos derivados; use una importación limpia")
        snapshots = source.execute("SELECT id,fecha_corte_utc FROM snapshots").fetchall()
        if len(snapshots) != 1:
            raise ValueError("El baseline requiere exactamente un snapshot")
        snapshot_id, cutoff = snapshots[0]
        rows = [dict(row) for row in source.execute("SELECT * FROM noticias")]
        if not rows:
            raise ValueError("No hay noticias válidas para procesar")
        groups = group_news(rows, threshold)
        target = sqlite3.connect(":memory:")
        target.row_factory = sqlite3.Row
        target.execute("PRAGMA foreign_keys=ON")
        source.backup(target)
        created = []
        with target:
            for members in groups:
                member_ids = [row["id"] for row in members]
                group_id = stable_id("GRP", member_ids)
                case_id = stable_id("CASO", member_ids)
                priority_id = stable_id("PRI", member_ids + [RULES_VERSION])
                theme, components, score, explanation, known = ranking(members, cutoff)
                target.execute("INSERT INTO grupos VALUES (?,?,?,?)",
                               (snapshot_id, group_id, theme, f"Baseline léxico: {len(members)} publicación(es)."))
                for row in members:
                    provenance = row["origen"].strip().lower() if row["origen"] else None
                    reason = "Procedencia declarada en el campo origen del CSV." if provenance else None
                    target.execute("INSERT INTO grupo_noticias VALUES (?,?,?,?,?)",
                                   (snapshot_id, group_id, row["id"], provenance, reason))
                evidence_state = "parcial" if known else "insuficiente"
                pending = "Confirmar relación con Panamá, consultar fuente primaria y obtener contenido autorizado."
                target.execute("INSERT INTO casos VALUES (?,?,?,?,?,?,?)",
                               (snapshot_id, case_id, group_id, "editorial", members[0]["titulo"], evidence_state, pending))
                for row in members:
                    evidence_id = stable_id("EVID", [row["id"], "titulo"])
                    target.execute("INSERT INTO evidencias VALUES (?,?,?,?,?,?)",
                                   (snapshot_id, evidence_id, row["id"], None, "titulo",
                                    "Basado únicamente en titular/metadatos; no confirma el hecho."))
                    target.execute("INSERT INTO caso_evidencias VALUES (?,?,?)",
                                   (snapshot_id, case_id, evidence_id))
                target.execute("INSERT INTO priorizaciones VALUES (?,?,?,?,?,?,?,?,?)",
                               (snapshot_id, priority_id, case_id, RULES_VERSION,
                                json.dumps(components, sort_keys=True), json.dumps(WEIGHTS, sort_keys=True),
                                score, json.dumps(explanation, ensure_ascii=False, sort_keys=True), cutoff))
                created.append({"caso_id": case_id, "grupo_id": group_id, "miembros": member_ids,
                                "puntaje": score, "componentes": components,
                                "procedencias_identificadas": known})
        validate_relations(target)
        if target.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("La agenda generada contiene relaciones inválidas")
        save_new(target, output_path)
        target.close()
        return {"reglas_version": RULES_VERSION, "umbral_similitud": threshold,
                "casos_creados": len(created), "casos": created,
                "advertencias": ["Baseline léxico, no IA semántica.",
                                  "La similitud no demuestra corroboración ni verdad.",
                                  "No se relacionaron indicadores automáticamente."]}
    finally:
        source.close()


def main():
    parser = argparse.ArgumentParser(description="Crear agenda explicable desde una base importada")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=.55)
    args = parser.parse_args()
    if not 0 <= args.threshold <= 1:
        raise SystemExit("threshold debe estar entre 0 y 1")
    print(json.dumps(process(args.input, args.output, args.threshold), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
