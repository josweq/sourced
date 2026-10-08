"""Generacion de versiones editables con modelo local y guardian."""
from __future__ import annotations

from src.editorial import criterios as criterios_mod
from src.editorial.cronometro import contar_palabras, estimar_segundos
from src.editorial.formatos import adaptar
from src.ia import guardian
from src.ia.proveedores import ProviderUnavailable, generar as generar_modelo


SCHEMA_VERSION = {
    "type": "object",
    "required": ["oraciones"],
    "properties": {
        "oraciones": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["texto", "evidencia_id"],
                "properties": {
                    "texto": {"type": "string"},
                    "evidencia_id": {"type": "string"},
                },
            },
        },
    },
}

PERMITIDAS_VERSION = {
    "boletin", "correo", "cercano", "duracion", "economia", "enfoque",
    "explicativo", "extension", "formato", "gente", "infantil", "jovenes",
    "lectores", "logistica", "ninos", "politica", "profesional", "publico",
    "push", "radio", "revista", "servicios", "sobrio", "turismo", "youtube",
}


def _afirmaciones(paquete: dict) -> list[dict]:
    afirmaciones = []
    vistos = set()
    for index, item in enumerate(paquete.get("afirmaciones") or [], 1):
        texto = str(item.get("texto") or "").strip()
        evidencia_id = item.get("evidencia_id")
        if not texto or not evidencia_id:
            continue
        clave = (evidencia_id, texto.lower())
        if clave in vistos:
            continue
        vistos.add(clave)
        afirmaciones.append({**item, "id": item.get("id") or f"AF-{index}"})
    return afirmaciones


def _evidencia_label(evidencia: dict | None) -> str:
    evidencia = evidencia or {}
    if evidencia.get("noticia_titulo"):
        return f"Titular · {evidencia.get('medio') or evidencia.get('fuente_nombre') or 'medio'}"
    if evidencia.get("indicador_id"):
        return f"Banco Mundial · {evidencia.get('pais_iso3') or ''} {evidencia.get('anio') or ''}".strip()
    return f"Evidencia · {evidencia.get('id') or 'sin ID'}"


def _preparar_afirmaciones(paquete: dict) -> list[dict]:
    evidencias = {e.get("id"): e for e in paquete.get("evidencias") or []}
    result = []
    for item in _afirmaciones(paquete):
        result.append({
            **item,
            "cita_label": item.get("cita_label") or _evidencia_label(evidencias.get(item.get("evidencia_id"))),
        })
    return result


def _normalizar_oraciones(data: dict, afirmaciones: list[dict]) -> list[dict]:
    ids = {str(item.get("evidencia_id")): item for item in afirmaciones}
    oraciones = []
    for index, item in enumerate(data.get("oraciones") or [], 1):
        texto = str(item.get("texto") or "").strip()
        evidencia_id = str(item.get("evidencia_id") or "").strip()
        if not texto or evidencia_id not in ids:
            continue
        base = ids[evidencia_id]
        oraciones.append({
            "id": item.get("id") or f"GEN-{index}",
            "texto": texto,
            "tipo": base.get("tipo", "declaracion"),
            "evidencia_id": evidencia_id,
            "campo": base.get("campo") or "titulo",
            "cita_label": base.get("cita_label") or evidencia_id,
        })
    return oraciones


def _texto(oraciones: list[dict]) -> str:
    return " ".join(f"{item['texto']} ({item.get('cita_label') or item['evidencia_id']})." for item in oraciones).strip()


def _objetivo(criterios: dict) -> dict:
    return {"palabras": criterios.get("palabras"), "segundos": criterios.get("duracion_s")}


def _alcance(texto: str, objetivo: dict) -> str:
    palabras = contar_palabras(texto)
    segundos = estimar_segundos(texto)
    partes = []
    if objetivo.get("palabras") and palabras < objetivo["palabras"] * 0.7:
        partes.append(f"{objetivo['palabras']} palabras")
    if objetivo.get("segundos") and segundos < objetivo["segundos"] * 0.7:
        partes.append(f"{objetivo['segundos']} s")
    if not partes:
        return ""
    return (
        f"Con la evidencia disponible alcanza para ~{palabras} palabras (~{segundos} s). "
        f"Para llegar a {' y '.join(partes)} hace falta la fuente primaria."
    )


def _respuesta(texto: str, oraciones: list[dict], retiradas: list[dict], criterios: dict,
               avisos: list[str], prompt: str, guardian_dict: dict) -> dict:
    palabras = contar_palabras(texto)
    segundos = estimar_segundos(texto)
    objetivo = _objetivo(criterios)
    return {
        "texto": texto,
        "oraciones": oraciones,
        "retiradas": retiradas,
        "criterios_aplicados": criterios,
        "criterios_etiquetas": criterios_mod.criterios_elegidos(criterios),
        "avisos": avisos,
        "palabras": palabras,
        "segundos_estimados": segundos,
        "objetivo": objetivo,
        "alcance": _alcance(texto, objetivo),
        "prompt": prompt,
        "guardian": guardian_dict,
    }


def _respaldo(paquete: dict, criterios: dict, avisos: list[str], prompt: str) -> dict:
    formato = criterios_mod.FORMATO_RESPALDO.get(criterios.get("formato"), "tv")
    tono = "explicativo" if criterios.get("tono") in {"explicativo", "infantil"} else "sobrio"
    enfasis = criterios.get("enfasis") or "noticia"
    adaptado = adaptar(paquete, formato, duracion_s=criterios.get("duracion_s"),
                       enfasis=enfasis, tono=tono)
    respaldo_avisos = list(avisos) + ["Generado sin modelo: versión armada desde las citas"]
    texto = adaptado.get("texto", "")
    return _respuesta(texto, adaptado.get("oraciones") or [], adaptado.get("retiradas") or [],
                      criterios, respaldo_avisos, prompt, adaptado.get("guardian") or {})


def generar_version(paquete_borrador: dict, criterios: dict, proveedor=generar_modelo,
                    timeout: int = 120) -> dict:
    afirmaciones = _preparar_afirmaciones(paquete_borrador)
    criterios, avisos = criterios_mod.ajustar_prudencia(afirmaciones, criterios)
    caso = paquete_borrador.get("caso") or {"titulo": paquete_borrador.get("titulo")}
    prompt = criterios_mod.construir_prompt_version(caso, afirmaciones, criterios)
    if not afirmaciones:
        return _respaldo(paquete_borrador, criterios, avisos, prompt)
    try:
        data = proveedor(prompt, SCHEMA_VERSION, timeout=timeout)
    except ProviderUnavailable:
        return _respaldo(paquete_borrador, criterios, avisos, prompt)
    candidatas = _normalizar_oraciones(data, afirmaciones)
    resultado = guardian.validar_oraciones(candidatas, paquete_borrador.get("evidencias") or [],
                                           permitidas=PERMITIDAS_VERSION)
    if not resultado.aceptadas:
        return _respaldo(paquete_borrador, criterios, avisos, prompt)
    texto = _texto(resultado.aceptadas)
    return _respuesta(texto, resultado.aceptadas, resultado.retiradas, criterios,
                      avisos, prompt, resultado.to_dict())
