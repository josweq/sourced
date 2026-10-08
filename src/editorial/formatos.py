"""Adaptacion determinista de borradores citados a formatos editoriales."""
from __future__ import annotations

import re

from src.editorial.cronometro import DEFAULT_PPM, resumen_cronometro
from src.ia import guardian


FORMATOS = {"tv", "radio", "vertical", "web", "alerta"}
ENFASIS = {"noticia", "dato", "verificacion"}
TONOS = {"sobrio", "explicativo"}
PALABRAS_FORMATOS = {
    "alcance", "bloque", "bloques", "contexto", "dato", "didactico",
    "explicativo", "formato", "indicador", "oficial", "primaria",
    "publicar", "radio", "titular", "vertical", "web",
}


def _evidencia_label(evidencia: dict | None) -> str:
    evidencia = evidencia or {}
    if evidencia.get("noticia_titulo"):
        return f"Titular · {evidencia.get('medio') or evidencia.get('fuente_nombre') or 'medio'}"
    if evidencia.get("indicador_id"):
        return f"Banco Mundial · {evidencia.get('pais_iso3') or ''} {evidencia.get('anio') or ''}".strip()
    return f"Evidencia · {evidencia.get('id') or 'sin ID'}"


def _normalizar_afirmaciones(paquete: dict) -> list[dict]:
    afirmaciones = paquete.get("afirmaciones") or []
    result = []
    vistas = set()
    for index, item in enumerate(afirmaciones, 1):
        texto = str(item.get("texto") or "").strip()
        evidencia_id = item.get("evidencia_id")
        if not texto or not evidencia_id:
            continue
        # El borrador repite cada afirmación en brief y guion (este con la etiqueta de cita al final):
        # se adapta una sola vez por evidencia y texto.
        clave = (evidencia_id, re.sub(r"\s*\([^)]*\)\.?$", "", texto).rstrip(". ").lower())
        if clave in vistas:
            continue
        vistas.add(clave)
        result.append({
            "id": item.get("id") or f"AF-{index}",
            "texto": texto,
            "tipo": item.get("tipo") or "declaracion",
            "evidencia_id": evidencia_id,
            "campo": item.get("campo") or "titulo",
            "cita_label": item.get("cita_label") or "",
            "prioridad": index,
        })
    return result


def _ordenar(afirmaciones: list[dict], enfasis: str) -> tuple[list[dict], bool]:
    indicadores = [a for a in afirmaciones if a.get("tipo") == "hecho" or a.get("campo") in {"valor", "anio", "unidad", "pais_iso3"}]
    otras = [a for a in afirmaciones if a not in indicadores]
    if enfasis == "dato":
        return (indicadores + otras if indicadores else afirmaciones), bool(indicadores)
    return afirmaciones, bool(indicadores)


def _recortar(oraciones: list[dict], duracion_s: int | None, maximo_palabras: int | None = None) -> tuple[list[dict], bool]:
    if duracion_s:
        maximo_palabras = max(1, round((int(duracion_s) / 60) * DEFAULT_PPM))
    if not maximo_palabras:
        return oraciones, False
    kept, total = [], 0
    for item in oraciones:
        words = len(guardian.tokens(item["texto"])) or len(item["texto"].split())
        if kept and total + words > maximo_palabras:
            return kept, True
        kept.append(item)
        total += words
        if total >= maximo_palabras:
            return kept, len(kept) < len(oraciones)
    return kept, len(kept) < len(oraciones)


def _faltante(paquete: dict, primera: dict | None) -> list[dict]:
    texto = str(paquete.get("preguntas_pendientes") or "Falta verificar fuente primaria, contexto y alcance antes de publicar.").strip()
    if not texto or not primera:
        return []
    if not texto.endswith((".", "?")):
        texto += "."
    return [{**primera, "id": "FALTA-1", "texto": f"Falta verificar: {texto}", "tipo": "hipotesis", "codigo": True}]


def _explicar(oraciones: list[dict], evidencias: list[dict], tono: str) -> list[dict]:
    """Frase en lenguaje llano armada solo con conteos de la evidencia; no añade hechos."""
    if tono != "explicativo" or not oraciones:
        return []
    medios = sorted({e.get("medio") for e in evidencias if e.get("noticia_titulo") and e.get("medio")})
    if len(medios) > 1:
        texto = f"En pocas palabras: {len(medios)} medios publicaron este tema ({', '.join(medios)}); aún no hay confirmación de una fuente primaria."
    elif medios:
        texto = f"En pocas palabras: por ahora solo {medios[0]} publicó este titular; aún no hay confirmación de otra fuente."
    else:
        texto = "En pocas palabras: el dato viene de una serie oficial anual; no describe la situación de hoy."
    return [{**oraciones[0], "id": "EXPL-1", "texto": texto, "tipo": "inferencia", "codigo": True}]


def _validar(oraciones: list[dict], evidencias: list[dict]) -> tuple[list[dict], list[dict], dict]:
    # El texto armado por código (qué falta, explicación) no afirma hechos: no pasa por el guardián.
    del_codigo = [o for o in oraciones if o.get("codigo")]
    resultado = guardian.validar_oraciones([o for o in oraciones if not o.get("codigo")], evidencias,
                                           permitidas=PALABRAS_FORMATOS)
    return resultado.aceptadas + del_codigo, resultado.retiradas, resultado.to_dict()


def _serializar(oraciones: list[dict]) -> str:
    return " ".join(item["texto"] for item in oraciones).strip()


def _bloques_vertical(oraciones: list[dict], faltantes: list[dict]) -> list[dict]:
    sabe = oraciones[1:]
    if not sabe and oraciones:
        # Con una sola afirmación no se repite: se dice que no hay más evidencia publicada.
        sabe = [{**oraciones[0], "id": "SABE-1", "codigo": True, "tipo": "inferencia",
                 "texto": "Por ahora no hay más evidencia publicada que este titular."}]
    return [
        {"titulo": "0-5 s · Lo que se reporta", "oraciones": oraciones[:1]},
        {"titulo": "5-45 s · Qué se sabe", "oraciones": sabe},
        {"titulo": "45-60 s · Qué falta verificar", "oraciones": faltantes},
    ]


def _web(oraciones: list[dict], faltantes: list[dict], tiene_indicador: bool, primero_falta: bool = False) -> list[dict]:
    if primero_falta:
        return [{"titulo": "Qué falta verificar", "oraciones": faltantes}] + _web(oraciones, [], tiene_indicador)[:-1]
    bloques = [{"titulo": "Qué se reporta", "oraciones": oraciones[:1]}]
    contexto = [item for item in oraciones[1:] if item.get("tipo") == "hecho" or item.get("campo") == "valor"]
    if tiene_indicador and contexto:
        bloques.append({"titulo": "Contexto", "oraciones": contexto})
    restantes = [item for item in oraciones[1:] if item not in contexto]
    if restantes:
        bloques.append({"titulo": "Qué se sabe", "oraciones": restantes})
    bloques.append({"titulo": "Qué falta verificar", "oraciones": faltantes})
    return bloques


def _alerta(oraciones: list[dict]) -> tuple[list[dict], bool]:
    if not oraciones:
        return [], False
    item = {**oraciones[0]}
    recortado = False
    if len(item["texto"]) > 140:
        corte = item["texto"][:140].rsplit(" ", 1)[0].rstrip(" ,;:")
        item["texto"] = corte.rstrip(".") + "."
        recortado = True
    return [item], recortado


def adaptar(paquete: dict, formato: str, *, duracion_s: int | None = None,
            enfasis: str = "noticia", tono: str = "sobrio") -> dict:
    """Devuelve una version adaptada sin persistir y sin agregar datos."""
    if formato not in FORMATOS:
        raise ValueError("Formato inválido")
    if enfasis not in ENFASIS:
        raise ValueError("Énfasis inválido")
    if tono not in TONOS:
        raise ValueError("Tono inválido")
    if duracion_s is not None and (not isinstance(duracion_s, int) or duracion_s <= 0 or duracion_s > 600):
        raise ValueError("duracion_s debe ser un entero entre 1 y 600")

    evidencias = list(paquete.get("evidencias") or [])
    by_id = {e.get("id"): e for e in evidencias}
    afirmaciones, tiene_indicador = _ordenar(_normalizar_afirmaciones(paquete), enfasis)
    for item in afirmaciones:
        if not item.get("cita_label"):
            item["cita_label"] = _evidencia_label(by_id.get(item["evidencia_id"]))

    avisos = ["Borrador generado por IA — requiere revisión humana"]
    if paquete.get("alcance_texto") == "titular_metadatos" or any(e.get("noticia_titulo") for e in evidencias):
        avisos.append("Basado únicamente en titular/metadatos")
    if enfasis == "dato" and not tiene_indicador:
        avisos.append("No hay indicador oficial citado; se abre con la noticia.")

    faltantes = _faltante(paquete, afirmaciones[0] if afirmaciones else None)
    explicacion = _explicar(afirmaciones, evidencias, tono)
    base = (faltantes + afirmaciones + explicacion) if enfasis == "verificacion" else (afirmaciones + explicacion)
    recortado = False
    if formato == "alerta":
        seleccion, recortado = _alerta(afirmaciones)
        bloques = [{"titulo": "Alerta", "oraciones": seleccion}]
    elif formato == "web":
        seleccion, recortado = _recortar(afirmaciones + explicacion, duracion_s, 220)
        bloques = _web(seleccion, faltantes, tiene_indicador, primero_falta=enfasis == "verificacion")
    else:
        objetivo = {"radio": 30, "vertical": 60, "tv": 60}[formato]
        if formato == "vertical":
            # El video vertical mantiene su estructura fija: lo reportado, lo que se sabe y lo que falta al final.
            seleccion, recortado = _recortar(afirmaciones + explicacion, duracion_s or objetivo)
            bloques = _bloques_vertical(seleccion, faltantes)
        else:
            seleccion, recortado = _recortar(base, duracion_s or objetivo)
            cierre = [] if enfasis == "verificacion" else faltantes
            bloques = [{"titulo": "Guion", "oraciones": seleccion + cierre}]

    candidatas = [item for bloque in bloques for item in bloque["oraciones"]]
    aceptadas, retiradas, veredicto = _validar(candidatas, evidencias)
    aceptadas_ids = {id(item) for item in aceptadas}
    bloques = [{**bloque, "oraciones": [item for item in bloque["oraciones"] if id(item) in aceptadas_ids]} for bloque in bloques]
    texto = "\n".join(
        f"{bloque['titulo']}\n" + _serializar(bloque["oraciones"])
        for bloque in bloques if bloque["oraciones"]
    ).strip()
    cronometro = resumen_cronometro(texto) if formato in {"tv", "radio", "vertical"} else None
    contador = {"palabras": len(texto.split())}
    if formato == "alerta":
        contador["caracteres"] = len(texto.replace("Alerta\n", "", 1))
    if formato == "web":
        contador["limite_palabras"] = 250
    if formato == "alerta":
        contador["limite_caracteres"] = 140

    return {
        "formato": formato,
        "duracion_s": duracion_s,
        "enfasis": enfasis,
        "tono": tono,
        "avisos": avisos,
        "bloques": bloques,
        "texto": texto,
        "oraciones": aceptadas,
        "retiradas": retiradas,
        "guardian": veredicto,
        "cronometro": cronometro,
        "contador": contador,
        "recortado": recortado,
        "payload_version": {
            "titulo": paquete.get("titulo") or "Borrador adaptado",
            "enfoque": paquete.get("enfoque") or "",
            "brief": texto if formato == "web" else paquete.get("brief", ""),
            "guion": texto if formato in {"tv", "radio", "vertical"} else paquete.get("guion", ""),
            "copy": texto.replace("Alerta\n", "", 1) if formato == "alerta" else paquete.get("copy", ""),
            "preguntas": paquete.get("preguntas") or [],
        },
    }
