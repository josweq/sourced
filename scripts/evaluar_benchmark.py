"""Ejecuta el benchmark de desarrollo contra la base de la demo y guarda salidas y métricas.

Uso:
    python scripts/evaluar_benchmark.py --db data/local/<base>.sqlite
Escribe evaluation/resultados/benchmark-<marca>.json y .md. Reporta numerador, denominador y cada fallo.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ia.consulta import responder  # noqa: E402

BENCHMARK = ROOT / "evaluation" / "benchmark" / "desarrollo.jsonl"


def evaluar_item(item, r):
    fallos = []
    texto = " ".join([r.get("respuesta", "")] + [a.get("texto", "") for a in r.get("afirmaciones", [])])
    avisos = " ".join([r.get("respuesta", "")] + list(r.get("vacios", [])))
    esperado = item.get("esperado", "cualquiera")
    if esperado != "cualquiera" and r["estado"] != esperado and not (esperado == "respondida" and r["estado"] == "contexto_sectorial"):
        fallos.append(f"estado {r['estado']} (esperado {esperado})")
    ids = {a.get("cita", {}).get("id") for a in r.get("afirmaciones", [])}
    if item.get("ids_esperados") and not ids & set(item["ids_esperados"]):
        fallos.append(f"no cita {item['ids_esperados']}")
    if item.get("texto_esperado") and item["texto_esperado"].lower() not in texto.lower():
        fallos.append(f"falta «{item['texto_esperado']}»")
    if item.get("aviso_esperado") and item["aviso_esperado"].lower() not in avisos.lower():
        fallos.append(f"falta aviso «{item['aviso_esperado']}»")
    for prohibido in item.get("texto_prohibido", []):
        if prohibido.lower() in texto.lower():
            fallos.append(f"contiene «{prohibido}»")
    if item.get("minimo_resultados") and len(r.get("afirmaciones", [])) < item["minimo_resultados"]:
        fallos.append("sin resultados")
    return fallos


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--salida", type=Path, default=ROOT / "evaluation" / "resultados")
    parser.add_argument("--modo", choices=("semantico", "lexico"), default="semantico",
                        help="lexico = línea base sin IA (palabras clave) con las mismas reglas de cifras y abstención")
    args = parser.parse_args()
    items = [json.loads(linea) for linea in BENCHMARK.read_text(encoding="utf-8").splitlines() if linea.strip()]
    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    responder(db, "calentamiento del modelo local")  # la primera carga no cuenta en la latencia
    filas = []
    for item in items:
        r = responder(db, item["pregunta"], modo=args.modo)
        fallos = evaluar_item(item, r)
        filas.append({"id": item["id"], "tipo": item["tipo"], "pregunta": item["pregunta"], "esperado": item.get("esperado"),
                      "observado": r["estado"], "metodo": r.get("metodo"), "latencia_ms": r["latencia_ms"],
                      "afirmaciones": len(r.get("afirmaciones", [])),
                      "afirmaciones_con_cita": sum(1 for a in r.get("afirmaciones", []) if a.get("cita", {}).get("id")),
                      "ok": not fallos, "fallos": fallos, "salida": r})
    por_tipo = {}
    for f in filas:
        t = por_tipo.setdefault(f["tipo"], [0, 0])
        t[0] += f["ok"]; t[1] += 1
    sin_resp = [f for f in filas if f["tipo"] == "sin_respuesta"]
    respondibles = [f for f in filas if f["tipo"] == "sustentada"]
    lat = sorted(f["latencia_ms"] for f in filas)
    total_af = sum(f["afirmaciones"] for f in filas)
    metricas = {
        "aciertos": [sum(f["ok"] for f in filas), len(filas)],
        "por_tipo": por_tipo,
        "abstencion_correcta": [sum(f["observado"] == "abstencion" for f in sin_resp), len(sin_resp)],
        "abstencion_indebida_en_sustentadas": [sum(f["observado"] == "abstencion" for f in respondibles), len(respondibles)],
        "cobertura_de_citas": [sum(f["afirmaciones_con_cita"] for f in filas), total_af],
        "latencia_ms": {"mediana": statistics.median(lat), "p95": lat[max(0, int(round(0.95 * len(lat))) - 1)], "max": lat[-1]},
        "validez_de_sustento": "pendiente de revisión humana (≥30 afirmaciones)",
        "etiquetado": "Preguntas y resultados esperados propuestos por Claude el 2026-10-07; revisión humana pendiente.",
    }
    marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    args.salida.mkdir(parents=True, exist_ok=True)
    base = args.salida / (f"benchmark-{marca}" + ("-lexico" if args.modo == "lexico" else ""))
    (base.with_suffix(".json")).write_text(json.dumps({"db": str(args.db), "metricas": metricas, "filas": filas},
                                                      ensure_ascii=False, indent=2), encoding="utf-8")
    pct = lambda par: f"{par[0]}/{par[1]}" + (f" ({100 * par[0] / par[1]:.0f} %)" if par[1] else "")
    md = [f"# Benchmark de desarrollo — {marca} — búsqueda {args.modo}", "",
          f"Base: `{args.db.name}` · 40 preguntas (20 sustentadas, 7 ambiguas/contradicción, 7 sin respuesta, 6 adversariales).",
          "Etiquetado: propuesto por Claude, **revisión humana pendiente**. No incluye el conjunto reservado del jurado.", "",
          "| Métrica | Resultado |", "|---|---|",
          f"| Aciertos totales | {pct(metricas['aciertos'])} |",
          *[f"| Aciertos · {t} | {pct(v)} |" for t, v in por_tipo.items()],
          f"| Abstención correcta (sin respuesta) | {pct(metricas['abstencion_correcta'])} |",
          f"| Abstención indebida (sustentadas) | {pct(metricas['abstencion_indebida_en_sustentadas'])} |",
          f"| Cobertura de citas | {pct(metricas['cobertura_de_citas'])} |",
          f"| Latencia mediana / p95 / máx. | {metricas['latencia_ms']['mediana']:.0f} / {metricas['latencia_ms']['p95']} / {metricas['latencia_ms']['max']} ms |",
          "| Validez de sustento | Pendiente de revisión humana |", "",
          "## Fallos", ""]
    fallidos = [f for f in filas if not f["ok"]]
    md += [f"- **{f['id']}** ({f['tipo']}) «{f['pregunta']}»: {'; '.join(f['fallos'])}" for f in fallidos] or ["_Ninguno._"]
    (base.with_suffix(".md")).write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
