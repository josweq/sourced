"""Prepara modelos locales: embeddings e5 y presencia de Ollama."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ia.embeddings import EXPECTED_DIM, VectorizadorE5, cache_huggingface_existe, nombre_modelo, vectorizar


def ollama_tiene_modelo(modelo: str) -> bool:
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and any(line.split()[0] == modelo for line in result.stdout.splitlines() if line.strip())


def main():
    parser = argparse.ArgumentParser(description="Descargar/verificar embeddings y comprobar Ollama local")
    parser.add_argument("--modelo-embeddings", default=nombre_modelo())
    parser.add_argument("--modelo-ollama", default="llama3.2:3b")
    args = parser.parse_args()
    errores = []
    try:
        model = VectorizadorE5(args.modelo_embeddings, permitir_descarga=True)
        vec = vectorizar(["prueba local"], tipo="passage", modelo=args.modelo_embeddings, model=model._model)
        if vec.shape != (1, EXPECTED_DIM):
            errores.append(f"Dimensión inesperada de embeddings: {vec.shape}; se esperaba 384.")
    except Exception as exc:
        errores.append(f"No se pudo preparar/verificar el modelo de embeddings {args.modelo_embeddings}: {exc}")
    if not cache_huggingface_existe(args.modelo_embeddings):
        errores.append(f"El modelo {args.modelo_embeddings} no quedó visible en la caché local.")
    if not ollama_tiene_modelo(args.modelo_ollama):
        errores.append(f"Ollama no tiene {args.modelo_ollama}. Instálalo manualmente con: ollama pull {args.modelo_ollama}")
    payload = {"modelo_embeddings": args.modelo_embeddings, "dim": EXPECTED_DIM,
               "modelo_ollama": args.modelo_ollama, "ok": not errores,
               "errores": errores}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if errores:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
