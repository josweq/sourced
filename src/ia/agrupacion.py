"""Agrupación semántica calibrable sin confundir repetición con corroboración."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from sklearn.metrics import precision_score, recall_score

from scripts.procesar_agenda import group_news as group_news_lexico, similarity, tokens
from src.ia.embeddings import vectorizar

RULES_VERSION = "ia-v1"


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def dias_separacion(a: dict, b: dict) -> float | None:
    da = _parse_date(a.get("fecha_publicacion") or a.get("fecha_deteccion"))
    db = _parse_date(b.get("fecha_publicacion") or b.get("fecha_deteccion"))
    if not da or not db:
        return None
    return abs((da - db).total_seconds()) / 86400


def coseno(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def agrupar_semantico(rows: Sequence[dict], vectores: np.ndarray | None = None, vectorizador=None,
                      umbral: float = 0.78, max_dias: int = 7,
                      umbral_muy_alto: float = 0.92) -> list[list[dict]]:
    if not rows:
        return []
    if vectores is None:
        vectores = (np.asarray(vectorizador([r["titulo"] for r in rows], tipo="passage"), dtype="float32")
                    if vectorizador else vectorizar([r["titulo"] for r in rows]))
    row_index = {id(row): idx for idx, row in enumerate(rows)}
    groups: list[list[dict]] = []
    group_vectors: list[np.ndarray] = []
    for idx, row in sorted(enumerate(rows), key=lambda item: item[1]["id"]):
        best_group, best_score = None, -1.0
        for group_idx, group in enumerate(groups):
            score = coseno(vectores[idx], group_vectors[group_idx])
            if score < umbral:
                continue
            separaciones = [dias_separacion(row, member) for member in group]
            fuera_ventana = any(value is not None and value > max_dias for value in separaciones)
            if fuera_ventana and score < umbral_muy_alto:
                continue
            if score > best_score:
                best_group, best_score = group_idx, score
        if best_group is None:
            groups.append([row])
            group_vectors.append(np.asarray(vectores[idx], dtype="float32"))
        else:
            groups[best_group].append(row)
            group_vectors[best_group] = np.mean([vectores[row_index[id(member)]] for member in groups[best_group]], axis=0)
            norm = np.linalg.norm(group_vectors[best_group]) or 1.0
            group_vectors[best_group] = group_vectors[best_group] / norm
    return groups


def evaluar_pares(rows: Sequence[dict], pares_csv: Path, vectorizador=None, umbral: float = 0.78) -> dict:
    por_id = {row["id"]: row for row in rows}
    if not pares_csv.exists():
        return {"advertencia": "No existe pares.csv; no se calculan métricas.", "pares": 0}
    pares = []
    with pares_csv.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row.get("id_a") in por_id and row.get("id_b") in por_id and row.get("mismo_evento") in {"0", "1"}:
                pares.append(row)
    if not pares:
        return {"advertencia": "No hay pares válidos; no se calculan métricas.", "pares": 0}
    titulos = [por_id[p["id_a"]]["titulo"] for p in pares] + [por_id[p["id_b"]]["titulo"] for p in pares]
    vecs = (np.asarray(vectorizador(titulos, tipo="passage"), dtype="float32")
            if vectorizador else vectorizar(titulos))
    n = len(pares)
    y = [int(p["mismo_evento"]) for p in pares]
    sem = [1 if coseno(vecs[i], vecs[i + n]) >= umbral else 0 for i in range(n)]
    jac = [1 if similarity(tokens(por_id[p["id_a"]]["titulo"]), tokens(por_id[p["id_b"]]["titulo"])) >= 0.55 else 0 for p in pares]
    return {
        "pares": n,
        "semantica": {"precision": precision_score(y, sem, zero_division=0),
                      "recall": recall_score(y, sem, zero_division=0),
                      "umbral": umbral},
        "jaccard_diego": {"precision": precision_score(y, jac, zero_division=0),
                          "recall": recall_score(y, jac, zero_division=0),
                          "umbral": 0.55},
        "nota": "Cada publicación, URL, medio y origen se conserva; procedencia solo sale de origen.",
    }
