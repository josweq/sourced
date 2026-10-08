"""Embeddings locales e5 con caché SQLite por modelo y texto."""
from __future__ import annotations

import functools

import hashlib
import os
from pathlib import Path
import sqlite3
from typing import Callable, Iterable, Sequence

import numpy as np

DEFAULT_MODEL = "intfloat/multilingual-e5-small"
EXPECTED_DIM = 384
PREFIXES = {"passage": "passage: ", "query": "query: "}


def nombre_modelo() -> str:
    return os.environ.get("LUPA_EMBEDDINGS", DEFAULT_MODEL)


def sha256_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def cache_huggingface_existe(modelo: str | None = None) -> bool:
    modelo = modelo or nombre_modelo()
    folder = "models--" + modelo.replace("/", "--")
    candidates = [
        Path(os.environ.get("LUPA_MODELOS_DIR", "")) / folder if os.environ.get("LUPA_MODELOS_DIR") else None,
        Path("modelos") / folder,
        Path(os.environ.get("TRANSFORMERS_CACHE", "")) / folder if os.environ.get("TRANSFORMERS_CACHE") else None,
        Path(os.environ.get("HF_HOME", "")) / "hub" / folder if os.environ.get("HF_HOME") else None,
        Path.home() / ".cache" / "huggingface" / "hub" / folder,
    ]
    return any(path and path.exists() for path in candidates)


def inicializar_cache(db: sqlite3.Connection) -> None:
    db.execute("""
      CREATE TABLE IF NOT EXISTS ia_embedding_cache (
        modelo TEXT NOT NULL,
        texto_sha256 TEXT NOT NULL,
        dim INTEGER NOT NULL,
        vector BLOB NOT NULL,
        PRIMARY KEY(modelo,texto_sha256)
      )
    """)


def vector_a_blob(vector: Sequence[float]) -> bytes:
    return np.asarray(vector, dtype="<f4").tobytes()


def blob_a_vector(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype="<f4").astype("float32")


def normalizar(vectores: np.ndarray) -> np.ndarray:
    normas = np.linalg.norm(vectores, axis=1, keepdims=True)
    normas[normas == 0] = 1.0
    return (vectores / normas).astype("float32")


class VectorizadorE5:
    def __init__(self, modelo: str | None = None, permitir_descarga: bool = False):
        self.modelo = modelo or nombre_modelo()
        local_only = cache_huggingface_existe(self.modelo)
        if not local_only and not permitir_descarga:
            raise RuntimeError(
                f"Modelo de embeddings no encontrado en caché: {self.modelo}. "
                "Ejecuta scripts/preparar_modelos.py con red antes de procesar."
            )
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(self.modelo, local_files_only=local_only and not permitir_descarga)

    def __call__(self, textos: Sequence[str], tipo: str = "passage") -> np.ndarray:
        return vectorizar(textos, tipo=tipo, modelo=self.modelo, model=self._model)


@functools.lru_cache(maxsize=2)
def _modelo_compartido(modelo: str, permitir_descarga: bool = False):
    """Carga el modelo una sola vez por proceso (recargarlo en cada consulta costaba segundos)."""
    return VectorizadorE5(modelo, permitir_descarga=permitir_descarga)._model


def _encode(textos_prefijados: Sequence[str], model=None, modelo: str | None = None,
            permitir_descarga: bool = False) -> np.ndarray:
    if model is None:
        model = _modelo_compartido(modelo or nombre_modelo(), permitir_descarga)
    vectores = model.encode(list(textos_prefijados), normalize_embeddings=True, convert_to_numpy=True)
    return normalizar(np.asarray(vectores, dtype="float32"))


def vectorizar(textos: Iterable[str], tipo: str = "passage", db: sqlite3.Connection | None = None,
               modelo: str | None = None, model=None, encoder: Callable[[Sequence[str]], np.ndarray] | None = None,
               permitir_descarga: bool = False) -> np.ndarray:
    """Devuelve embeddings normalizados; usa caché si recibe conexión SQLite."""
    if tipo not in PREFIXES:
        raise ValueError("tipo debe ser 'passage' o 'query'")
    modelo = modelo or nombre_modelo()
    textos = ["" if texto is None else str(texto) for texto in textos]
    if not textos:
        return np.zeros((0, EXPECTED_DIM), dtype="float32")
    if db is None:
        prefijados = [PREFIXES[tipo] + texto for texto in textos]
        return encoder(prefijados) if encoder else _encode(prefijados, model=model, modelo=modelo,
                                                           permitir_descarga=permitir_descarga)
    inicializar_cache(db)
    salida: list[np.ndarray | None] = [None] * len(textos)
    pendientes: list[tuple[int, str, str]] = []
    for idx, texto in enumerate(textos):
        digest = sha256_texto(PREFIXES[tipo] + texto)
        row = db.execute("""SELECT vector,dim FROM ia_embedding_cache
                            WHERE modelo=? AND texto_sha256=?""", (modelo, digest)).fetchone()
        if row:
            vector = blob_a_vector(row[0] if not isinstance(row, sqlite3.Row) else row["vector"])
            salida[idx] = vector
        else:
            pendientes.append((idx, texto, digest))
    if pendientes:
        prefijados = [PREFIXES[tipo] + texto for _, texto, _ in pendientes]
        nuevos = encoder(prefijados) if encoder else _encode(prefijados, model=model, modelo=modelo,
                                                             permitir_descarga=permitir_descarga)
        with db:
            for (idx, _, digest), vector in zip(pendientes, nuevos):
                vector = np.asarray(vector, dtype="float32")
                salida[idx] = vector
                db.execute("""INSERT OR REPLACE INTO ia_embedding_cache
                              (modelo,texto_sha256,dim,vector) VALUES (?,?,?,?)""",
                           (modelo, digest, int(vector.shape[0]), vector_a_blob(vector)))
    return np.vstack([np.asarray(vector, dtype="float32") for vector in salida])

