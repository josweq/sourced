"""Clasificación temática supervisada y comparaciones honestas."""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata
from typing import Callable, Iterable, Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from src.ia.embeddings import vectorizar

TOPICS = ("economia", "logistica_canal", "turismo", "servicios_publicos",
          "eventos_naturales", "regulacion")
SIN_CLASIFICAR = "sin_clasificar"
# «sin_clasificar» es una clase etiquetada por personas; un umbral de confianza extra la duplicaba.
# Calibrado 2026-10-08 con validación cruzada sobre 189 etiquetas: con 0,45 ningún titular
# recibía tema (confianza máxima mediana 0,20); con 0,0 macro-F1 0,479.
UMBRAL_INICIAL = 0.0

# Baseline documentado: reglas léxicas deliberadamente simples para comparación.
REGLAS_TEMATICAS = {
    "economia": ("economia", "economico", "dolar", "inflacion", "mercado", "empleo", "precio", "presupuesto"),
    "logistica_canal": ("canal", "puerto", "logistica", "buque", "contenedor", "aduana", "transito"),
    "turismo": ("turismo", "turista", "hotel", "viajero", "playa", "aeropuerto", "visitante"),
    "servicios_publicos": ("agua", "luz", "energia", "transporte", "metro", "salud", "escuela", "servicio"),
    "eventos_naturales": ("sismo", "lluvia", "inundacion", "huracan", "clima", "temblor", "deslizamiento"),
    "regulacion": ("ley", "decreto", "regulacion", "gobierno", "asamblea", "norma", "tribunal", "resolucion"),
}

PROTOTIPOS = {
    "economia": "Noticias de economía, empleo, precios, inflación, comercio y presupuesto público.",
    "logistica_canal": "Noticias del Canal de Panamá, puertos, transporte marítimo, carga y logística.",
    "turismo": "Noticias de turismo, hoteles, viajes, visitantes, playas y actividad turística.",
    "servicios_publicos": "Noticias de agua, energía, transporte público, salud, educación y servicios básicos.",
    "eventos_naturales": "Noticias de lluvias, sismos, inundaciones, clima, riesgos naturales y emergencias.",
    "regulacion": "Noticias de leyes, decretos, decisiones judiciales, regulación y trámites del gobierno.",
}


def normalizar_texto(texto: str) -> str:
    plain = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", plain))


def clasificar_reglas(titulo: str) -> tuple[str, str]:
    tokens = set(normalizar_texto(titulo).split())
    puntajes = {tema: len(tokens & set(claves)) for tema, claves in REGLAS_TEMATICAS.items()}
    tema, score = max(puntajes.items(), key=lambda item: (item[1], item[0]))
    if score <= 0:
        return SIN_CLASIFICAR, "Sin palabras clave temáticas."
    usadas = sorted(tokens & set(REGLAS_TEMATICAS[tema]))
    return tema, "Palabras clave: " + ", ".join(usadas)


def cargar_etiquetas(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            etiqueta = (row.get("etiqueta_humana") or "").strip()
            if etiqueta:
                rows.append({"id_noticia": row.get("id_noticia", "").strip(),
                             "titulo": row.get("titulo", "").strip(),
                             "etiqueta_humana": etiqueta})
    return rows


def _vectorizar_titulos(titulos: Sequence[str], vectorizador=None, tipo: str = "passage") -> np.ndarray:
    if vectorizador:
        return np.asarray(vectorizador(titulos, tipo=tipo), dtype="float32")
    return vectorizar(titulos, tipo=tipo)


def _cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.asarray(a, dtype="float32") @ np.asarray(b, dtype="float32").T


def clasificar_prototipos(titulos: Sequence[str], vectorizador=None) -> list[str]:
    if not titulos:
        return []
    proto_temas = list(PROTOTIPOS)
    proto_vec = _vectorizar_titulos([PROTOTIPOS[t] for t in proto_temas], vectorizador, tipo="passage")
    title_vec = _vectorizar_titulos(titulos, vectorizador, tipo="query")
    sims = _cosine_matrix(title_vec, proto_vec)
    return [proto_temas[int(np.argmax(row))] for row in sims]


def sin_clases_pequenas(rows: Sequence[dict], k: int = 5) -> tuple[list[dict], dict]:
    """Quita del entrenamiento las clases con menos de k ejemplos humanos (se declaran, no se inventan).

    Caso real 2026-10-08: una sola etiqueta «logistica_canal» impedía entrenar todo el modelo.
    """
    counts = Counter(row["etiqueta_humana"] for row in rows)
    excluidas = {tema: n for tema, n in counts.items() if n < k}
    return [row for row in rows if row["etiqueta_humana"] not in excluidas], excluidas


def conjunto_suficiente(etiquetas: Sequence[str], k: int = 5) -> tuple[bool, str]:
    counts = Counter(etiquetas)
    if len(counts) < 2:
        return False, "Se requieren al menos dos temas etiquetados para entrenar."
    bajos = {tema: n for tema, n in counts.items() if n < k}
    if bajos:
        return False, f"Hay temas con menos de {k} ejemplos: {bajos}. No se inventan métricas."
    return True, "Conjunto suficiente para validación cruzada estratificada."


def evaluar(csv_path: Path = Path("evaluation/etiquetas/temas.csv"),
            salida_dir: Path = Path("evaluation/resultados"), vectorizador=None,
            fecha: str | None = None) -> dict:
    rows, excluidas = sin_clases_pequenas(cargar_etiquetas(csv_path))
    fecha = fecha or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    salida_dir.mkdir(parents=True, exist_ok=True)
    y = [row["etiqueta_humana"] for row in rows]
    titulos = [row["titulo"] for row in rows]
    report: dict = {
        "fecha_utc": fecha,
        "archivo_etiquetas": str(csv_path),
        "tamano_conjunto": {"numerador": len(rows), "denominador": len(rows)},
        "metodo_etiquetado": "CSV de etiquetas humanas; filas vacías ignoradas.",
        "conteo_por_tema": dict(Counter(y)),
        "metricas": {},
        "advertencias": [f"Clases fuera del entrenamiento por tener menos de 5 ejemplos: {excluidas}."] if excluidas else [],
    }
    if not rows:
        report["advertencias"].append("No hay etiquetas humanas; no se calculan métricas.")
        _guardar_reporte(report, salida_dir, fecha)
        return report
    labels = sorted(set(y))
    reglas = [clasificar_reglas(t)[0] for t in titulos]
    protos = clasificar_prototipos(titulos, vectorizador)
    report["metricas"]["reglas_tematicas"] = _metricas(y, reglas, labels)
    report["metricas"]["prototipos_e5_zero_shot"] = _metricas(y, protos, labels)
    ok, reason = conjunto_suficiente(y)
    if ok:
        x = _vectorizar_titulos(titulos, vectorizador)
        clf = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        pred = cross_val_predict(clf, x, y, cv=cv)
        report["metricas"]["logreg_supervisado"] = _metricas(y, pred, labels)
    else:
        report["advertencias"].append(reason)
    _guardar_reporte(report, salida_dir, fecha)
    return report


def _metricas(y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str]) -> dict:
    return {
        "macro_f1": {"valor": f1_score(y_true, y_pred, labels=list(labels), average="macro", zero_division=0),
                     "numerador": int(sum(1 for a, b in zip(y_true, y_pred) if a == b)),
                     "denominador": len(y_true)},
        "por_tema": classification_report(y_true, y_pred, labels=list(labels), output_dict=True,
                                           zero_division=0),
        "matriz_confusion": {"labels": list(labels),
                             "valores": confusion_matrix(y_true, y_pred, labels=list(labels)).tolist()},
    }


def _guardar_reporte(report: dict, salida_dir: Path, fecha: str) -> None:
    json_path = salida_dir / f"clasificacion-{fecha}.json"
    md_path = salida_dir / f"clasificacion-{fecha}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Reporte de clasificación temática", "",
             f"Fecha UTC: `{report['fecha_utc']}`",
             f"Conjunto: {report['tamano_conjunto']['numerador']}/{report['tamano_conjunto']['denominador']} filas etiquetadas.",
             f"Método de etiquetado: {report['metodo_etiquetado']}", ""]
    for name, data in report["metricas"].items():
        lines += [f"## {name}", f"- Macro-F1: {data['macro_f1']['valor']:.4f} ({data['macro_f1']['numerador']}/{data['macro_f1']['denominador']} aciertos exactos).",
                  f"- Matriz de confusión labels={data['matriz_confusion']['labels']}",
                  f"- Valores: `{data['matriz_confusion']['valores']}`", ""]
    if report["advertencias"]:
        lines += ["## Advertencias", *[f"- {item}" for item in report["advertencias"]], ""]
    md_path.write_text("\n".join(lines), encoding="utf-8")


@dataclass
class ClasificadorTema:
    modelo: LogisticRegression
    etiquetas: list[str]
    titulos: list[str]
    vectores: np.ndarray
    vectorizador: Callable | None = None
    umbral: float = UMBRAL_INICIAL

    @classmethod
    def entrenar(cls, rows: Sequence[dict], vectorizador=None, umbral: float = UMBRAL_INICIAL):
        rows = [row for row in rows if row.get("etiqueta_humana")]
        if len({row["etiqueta_humana"] for row in rows}) < 2:
            raise ValueError("Se requieren al menos dos temas etiquetados para entrenar.")
        titulos = [row["titulo"] for row in rows]
        y = [row["etiqueta_humana"] for row in rows]
        x = _vectorizar_titulos(titulos, vectorizador)
        modelo = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
        modelo.fit(x, y)
        return cls(modelo=modelo, etiquetas=y, titulos=titulos, vectores=x,
                   vectorizador=vectorizador, umbral=umbral)

    def predecir(self, titulos: Iterable[str]) -> list[dict]:
        titulos = list(titulos)
        x = _vectorizar_titulos(titulos, self.vectorizador)
        probs = self.modelo.predict_proba(x)
        sims = _cosine_matrix(x, self.vectores)
        resultados = []
        for titulo, prob_row, sim_row in zip(titulos, probs, sims):
            idx = int(np.argmax(prob_row))
            prob = float(prob_row[idx])
            tema = str(self.modelo.classes_[idx])
            vecinos_idx = np.argsort(-sim_row)[:3]
            vecinos = [{"titulo": self.titulos[i], "etiqueta": self.etiquetas[i],
                        "similitud": round(float(sim_row[i]), 4)} for i in vecinos_idx]
            if prob < self.umbral:
                resultados.append({"tema": SIN_CLASIFICAR, "probabilidad": prob,
                                   "motivo": "confianza baja", "vecinos": vecinos})
            else:
                resultados.append({"tema": tema, "probabilidad": prob,
                                   "motivo": "Vecinos etiquetados más cercanos.", "vecinos": vecinos})
        return resultados

