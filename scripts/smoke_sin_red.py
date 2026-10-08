"""Prueba de humo para T10 (sin internet): ejerce las piezas locales y sale 0 solo si todas funcionan.

Uso:
    python scripts/smoke_sin_red.py --db data/local/<base>.sqlite
Se combina con la skill ia-local-verificable (corrida-sin-red.mjs --comando "...") para probar,
con la red cortada, que nada sale del equipo. Prohíbe descargas de modelos (modo sin conexión de
Hugging Face) y solo habla con Ollama en 127.0.0.1.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import urllib.request

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ia.consulta import responder  # noqa: E402


def paso(nombre, fn, resultados):
    inicio = time.perf_counter()
    try:
        detalle = fn()
        resultados.append({"paso": nombre, "ok": True, "ms": round((time.perf_counter() - inicio) * 1000), "detalle": detalle})
    except Exception as exc:  # noqa: BLE001 - se reporta cada fallo
        resultados.append({"paso": nombre, "ok": False, "ms": round((time.perf_counter() - inicio) * 1000), "detalle": str(exc)[:300]})


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--ollama", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    resultados = []

    def pregunta_con_evidencia():
        r = responder(db, "contrato de laptops del Meduca")
        assert r["estado"] == "respondida" and r["afirmaciones"], r["estado"]
        return f"{len(r['afirmaciones'])} afirmaciones citadas"

    def pregunta_sin_evidencia():
        r = responder(db, "precio del oro en Bolivia")
        assert r["estado"] == "abstencion", r["estado"]
        return "abstención"

    def cifra_oficial():
        r = responder(db, "inflación de Panamá hoy")
        assert "no es una medición actual" in r["afirmaciones"][0]["texto"]
        return r["afirmaciones"][0]["texto"][:60]

    def redaccion_local():
        cuerpo = json.dumps({"model": os.environ.get("LUPA_MODELO_REDACCION", "llama3.2:3b"),
                             "prompt": "Responde solo: listo", "stream": False,
                             "options": {"num_predict": 5}}).encode()
        req = urllib.request.Request(f"{args.ollama}/api/generate", cuerpo, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.load(resp).get("response", "")[:40]

    def adaptacion():
        from src.editorial.formatos import adaptar
        paquete = {"alcance_texto": "titular_metadatos", "afirmaciones": [
            {"id": "A1", "texto": "TVN reporta en titular: prueba sin red.", "evidencia_id": "E1", "campo": "titulo"}],
            "evidencias": [{"id": "E1", "campo": "titulo", "noticia_titulo": "Prueba sin red", "medio": "TVN"}]}
        return adaptar(paquete, "vertical")["texto"].splitlines()[0]

    paso("pregunta con evidencia (embeddings locales)", pregunta_con_evidencia, resultados)
    paso("pregunta sin evidencia (abstención)", pregunta_sin_evidencia, resultados)
    paso("cifra oficial del snapshot", cifra_oficial, resultados)
    paso("redacción con Ollama local", redaccion_local, resultados)
    paso("adaptación de formato", adaptacion, resultados)

    for r in resultados:
        print(f"{'OK   ' if r['ok'] else 'FALLA'} {r['paso']} · {r['ms']} ms · {r['detalle']}")
    sys.exit(0 if all(r["ok"] for r in resultados) else 1)


if __name__ == "__main__":
    main()
