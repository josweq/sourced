"""Búsqueda híbrida: baseline léxico + semántica con explicación."""
from __future__ import annotations

import time
from typing import Iterable, Sequence

import numpy as np

from scripts.procesar_agenda import similarity, tokens
from src.ia.embeddings import vectorizar


def reciprocal_rank_fusion(rankings: Sequence[Sequence[str]], k: int = 60) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return scores


def buscar(query: str, documentos: Sequence[dict], modo: str = "hibrida", vectorizador=None,
           umbral_semantico: float = 0.30, limite: int = 10) -> dict:
    """Busca documentos con campos id, titulo y opcional puntaje."""
    if modo not in {"palabras", "semantica", "hibrida"}:
        raise ValueError("modo debe ser palabras, semantica o hibrida")
    started = time.perf_counter()
    wanted = tokens(query)
    lexical = []
    for doc in documentos:
        score = similarity(wanted, tokens(doc.get("titulo", ""))) if wanted else 0.0
        if score > 0 or not wanted:
            lexical.append((doc["id"], score))
    lexical.sort(key=lambda item: (-item[1], item[0]))
    semantic = []
    if query and modo in {"semantica", "hibrida"} and documentos:
        qv = (np.asarray(vectorizador([query], tipo="query"), dtype="float32")
              if vectorizador else vectorizar([query], tipo="query"))[0]
        dv = (np.asarray(vectorizador([doc.get("titulo", "") for doc in documentos], tipo="passage"), dtype="float32")
              if vectorizador else vectorizar([doc.get("titulo", "") for doc in documentos], tipo="passage"))
        for doc, score in zip(documentos, dv @ qv):
            semantic.append((doc["id"], float(score)))
        semantic.sort(key=lambda item: (-item[1], item[0]))
    if modo == "palabras":
        ordered_ids = [doc_id for doc_id, _ in lexical]
        fusion = {doc_id: score for doc_id, score in lexical}
    elif modo == "semantica":
        ordered_ids = [doc_id for doc_id, score in semantic if score >= umbral_semantico]
        fusion = {doc_id: score for doc_id, score in semantic}
    else:
        rankings = []
        if lexical:
            rankings.append([doc_id for doc_id, _ in lexical])
        if semantic and semantic[0][1] >= umbral_semantico:
            rankings.append([doc_id for doc_id, _ in semantic])
        fusion = reciprocal_rank_fusion(rankings) if rankings else {}
        ordered_ids = sorted(fusion, key=lambda doc_id: (-fusion[doc_id], doc_id))
    by_id = {doc["id"]: doc for doc in documentos}
    lex_scores = dict(lexical)
    sem_scores = dict(semantic)
    results = []
    for doc_id in ordered_ids[:limite]:
        doc = dict(by_id[doc_id])
        por_palabras = lex_scores.get(doc_id, 0) > 0 or (not wanted and modo != "semantica")
        por_significado = sem_scores.get(doc_id, -1) >= umbral_semantico
        if por_palabras and por_significado:
            motivo = "Coincidió por palabras y por significado."
        elif por_significado:
            motivo = "Coincidió por significado."
        elif por_palabras:
            motivo = "Coincidió por palabras."
        else:
            motivo = "Coincidió por fusión de rangos."
        doc.update({"puntaje_hibrido": round(float(fusion.get(doc_id, 0.0)), 6),
                    "relevancia_textual": round(float(lex_scores.get(doc_id, 0.0)), 4),
                    "relevancia_semantica": round(float(sem_scores.get(doc_id, 0.0)), 4) if semantic else None,
                    "motivo": motivo})
        results.append(doc)
    best_sem = semantic[0][1] if semantic else None
    abstencion = not results or (modo in {"semantica", "hibrida"} and best_sem is not None and best_sem < umbral_semantico)
    return {"consulta": query, "modo": modo, "resultados": [] if abstencion else results,
            "abstencion": abstencion,
            "motivo_abstencion": "El mejor puntaje semántico quedó bajo el umbral calibrado." if abstencion else None,
            "umbral_semantico": umbral_semantico,
            "tiempo_ms": round((time.perf_counter() - started) * 1000, 3)}
