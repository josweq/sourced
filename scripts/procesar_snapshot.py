"""Tubería IA: embeddings, tema, grupos semánticos, casos y ranking."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from scripts.modelo_datos import save_new, validate_relations
    from scripts.procesar_agenda import stable_id, ranking, WEIGHTS
except ModuleNotFoundError:
    from modelo_datos import save_new, validate_relations
    from procesar_agenda import stable_id, ranking, WEIGHTS

from src.ia.agrupacion import RULES_VERSION, agrupar_semantico, evaluar_pares
from src.ia.clasificador import ClasificadorTema, cargar_etiquetas, clasificar_reglas, conjunto_suficiente
from src.ia.contradicciones import detectar as detectar_contradicciones
from src.ia.embeddings import EXPECTED_DIM, blob_a_vector, nombre_modelo, vector_a_blob, vectorizar
from src.ia.proveedores import ProviderUnavailable
from src.ia.redaccion import cargar_evidencias_caso, generar_paquete, guardar_borrador


def crear_tablas_ia(db):
    db.execute("""
      CREATE TABLE IF NOT EXISTS ia_embeddings (
        snapshot_id TEXT NOT NULL,
        noticia_id TEXT NOT NULL,
        modelo TEXT NOT NULL,
        dim INTEGER NOT NULL,
        vector BLOB NOT NULL,
        PRIMARY KEY(snapshot_id,noticia_id,modelo)
      )
    """)
    db.execute("""
      CREATE TABLE IF NOT EXISTS ia_clasificaciones (
        snapshot_id TEXT NOT NULL,
        noticia_id TEXT NOT NULL,
        tema TEXT NOT NULL,
        probabilidad REAL NOT NULL,
        metodo TEXT NOT NULL,
        motivo TEXT NOT NULL,
        PRIMARY KEY(snapshot_id,noticia_id,metodo)
      )
    """)
    db.execute("""
      CREATE TABLE IF NOT EXISTS ia_contradicciones (
        snapshot_id TEXT NOT NULL,
        caso_id TEXT NOT NULL,
        ordinal INTEGER NOT NULL,
        hallazgo_json TEXT NOT NULL,
        PRIMARY KEY(snapshot_id,caso_id,ordinal)
      )
    """)


def _clasificar(rows, etiquetas_path, vectorizador=None, umbral=.45):
    etiquetas = cargar_etiquetas(etiquetas_path)
    ok, reason = conjunto_suficiente([r["etiqueta_humana"] for r in etiquetas])
    if ok:
        clf = ClasificadorTema.entrenar(etiquetas, vectorizador=vectorizador, umbral=umbral)
        preds = clf.predecir([row["titulo"] for row in rows])
        return preds, "logreg-v1", reason
    preds = []
    for row in rows:
        tema, motivo = clasificar_reglas(row["titulo"])
        preds.append({"tema": tema, "probabilidad": 1.0 if tema != "sin_clasificar" else 0.0,
                      "motivo": "Fallback por reglas temáticas: " + motivo, "vecinos": []})
    return preds, "reglas-tematicas-v1", reason


def process(input_path: Path, output_path: Path, etiquetas_path: Path = Path("evaluation/etiquetas/temas.csv"),
            pares_path: Path = Path("evaluation/etiquetas/pares.csv"), umbral_tema: float = .45,
            umbral_grupo: float = .945, max_dias: int = 7, vectorizador=None, borradores: int = 0):
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
            raise ValueError("La tubería requiere exactamente un snapshot")
        snapshot_id, cutoff = snapshots[0]
        rows = [dict(row) for row in source.execute("SELECT * FROM noticias")]
        if not rows:
            raise ValueError("No hay noticias válidas para procesar")
        target = sqlite3.connect(":memory:")
        target.row_factory = sqlite3.Row
        target.execute("PRAGMA foreign_keys=ON")
        source.backup(target)
        crear_tablas_ia(target)
        modelo = nombre_modelo()
        vectores = vectorizar([row["titulo"] for row in rows], tipo="passage", db=target,
                              modelo=modelo, encoder=(lambda pref: vectorizador([p.split(": ", 1)[1] for p in pref], tipo="passage")) if vectorizador else None)
        preds, metodo_tema, motivo_tema = _clasificar(rows, etiquetas_path, vectorizador, umbral_tema)
        with target:
            for row, vector, pred in zip(rows, vectores, preds):
                target.execute("""INSERT INTO ia_embeddings VALUES (?,?,?,?,?)""",
                               (snapshot_id, row["id"], modelo, int(vector.shape[0]), vector_a_blob(vector)))
                target.execute("""UPDATE noticias SET tema=? WHERE snapshot_id=? AND id=?""",
                               (pred["tema"], snapshot_id, row["id"]))
                target.execute("""INSERT INTO ia_clasificaciones VALUES (?,?,?,?,?,?)""",
                               (snapshot_id, row["id"], pred["tema"], float(pred["probabilidad"]),
                                metodo_tema, pred["motivo"]))
                row["tema"] = pred["tema"]
            groups = agrupar_semantico(rows, vectores=vectores, umbral=umbral_grupo, max_dias=max_dias)
            created = []
            contradicciones_reporte = []
            for members in groups:
                member_ids = [row["id"] for row in members]
                group_id = stable_id("GRP", member_ids)
                case_id = stable_id("CASO", member_ids)
                priority_id = stable_id("PRI", member_ids + [RULES_VERSION])
                theme, components, score, explanation, known = ranking(members, cutoff)
                target.execute("INSERT INTO grupos VALUES (?,?,?,?)",
                               (snapshot_id, group_id, theme,
                                f"Agrupación semántica ia-v1: {len(members)} publicación(es)."))
                for row in members:
                    provenance = row["origen"].strip().lower() if row["origen"] else None
                    reason = "Procedencia declarada en origen; repetición no implica corroboración." if provenance else None
                    target.execute("INSERT INTO grupo_noticias VALUES (?,?,?,?,?)",
                                   (snapshot_id, group_id, row["id"], provenance, reason))
                hallazgos = detectar_contradicciones([
                    {"noticia_id": row["id"], "titulo": row["titulo"], "medio": row["medio"]}
                    for row in members
                ])
                evidence_state = "parcial" if known else "insuficiente"
                pending = "Confirmar fuente primaria, relación con Panamá y contenido autorizado antes de publicar."
                if hallazgos:
                    evidence_state = "insuficiente"
                    resumen = "; ".join(h["explicacion"] for h in hallazgos)
                    pending = f"Cifras incompatibles entre medios: {resumen}. {pending}"
                target.execute("INSERT INTO casos VALUES (?,?,?,?,?,?,?)",
                               (snapshot_id, case_id, group_id, "editorial", members[0]["titulo"], evidence_state, pending))
                for ordinal, hallazgo in enumerate(hallazgos, 1):
                    target.execute("INSERT INTO ia_contradicciones VALUES (?,?,?,?)",
                                   (snapshot_id, case_id, ordinal,
                                    json.dumps(hallazgo, ensure_ascii=False, sort_keys=True)))
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
                                "puntaje": score, "procedencias_identificadas": known})
                if hallazgos:
                    contradicciones_reporte.append({"caso_id": case_id, "hallazgos": hallazgos})
        borradores_resultado = []
        for item in sorted(created, key=lambda row: (-row["puntaje"], row["caso_id"]))[:max(0, borradores)]:
            try:
                case, evidences = cargar_evidencias_caso(target, item["caso_id"])
                package = generar_paquete(case, evidences)
                if package.get("estado") == "abstencion" and not package.get("afirmaciones"):
                    borradores_resultado.append({"caso_id": item["caso_id"], "estado": "sin_borrador",
                                                 "motivo": package.get("explicacion")})
                    continue
                saved = guardar_borrador(target, item["caso_id"], package, "modelo")
                borradores_resultado.append({"caso_id": item["caso_id"], "estado": package.get("estado"),
                                             "borrador_id": saved["id"], "tiempo_ms": package.get("tiempo_ms")})
            except ProviderUnavailable as exc:
                borradores_resultado.append({"caso_id": item["caso_id"], "estado": "sin_borrador",
                                             "motivo": str(exc)})
            except Exception as exc:
                borradores_resultado.append({"caso_id": item["caso_id"], "estado": "sin_borrador",
                                             "motivo": f"Error de redaccion: {exc}"})
        validate_relations(target)
        fk = target.execute("PRAGMA foreign_key_check").fetchall()
        if fk:
            raise ValueError("La base generada contiene relaciones inválidas")
        save_new(target, output_path)
        reporte = {
            "reglas_version": RULES_VERSION,
            "modelo_embeddings": modelo,
            "dim": EXPECTED_DIM,
            "metodo_tema": metodo_tema,
            "motivo_tema": motivo_tema,
            "umbral_tema": umbral_tema,
            "umbral_grupo": umbral_grupo,
            "max_dias": max_dias,
            "noticias": len(rows),
            "temas": dict(Counter(row["tema"] for row in rows)),
            "casos_creados": len(created),
            "casos": created,
            "contradicciones": contradicciones_reporte,
            "borradores": borradores_resultado,
            "evaluacion_pares": evaluar_pares(rows, pares_path, vectorizador=vectorizador, umbral=umbral_grupo),
            "advertencias": [
                "Las publicaciones se conservan con URL, medio y origen.",
                "La procedencia se calcula solo desde origen; repetición no equivale a corroboración.",
                "La importación original queda intacta; esta es una base derivada nueva.",
            ],
        }
        report_path = output_path.with_suffix(output_path.suffix + ".reporte-ia.json")
        if report_path.exists():
            raise FileExistsError("El reporte ya existe; no se sobrescribe")
        report_path.write_text(json.dumps(reporte, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        target.close()
        return reporte
    finally:
        source.close()


def main():
    parser = argparse.ArgumentParser(description="Crear base derivada con capa IA local")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--etiquetas", type=Path, default=Path("evaluation/etiquetas/temas.csv"))
    parser.add_argument("--pares", type=Path, default=Path("evaluation/etiquetas/pares.csv"))
    parser.add_argument("--umbral-tema", type=float, default=.45)
    parser.add_argument("--umbral-grupo", type=float, default=.945)
    parser.add_argument("--max-dias", type=int, default=7)
    parser.add_argument("--borradores", type=int, default=8,
                        help="Genera borradores para los N casos de mayor prioridad (0 para omitir).")
    args = parser.parse_args()
    print(json.dumps(process(args.input, args.output, args.etiquetas, args.pares,
                             args.umbral_tema, args.umbral_grupo, args.max_dias,
                             borradores=args.borradores),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
