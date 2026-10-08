"""Guardian determinista para borradores citados."""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


PALABRAS_PERMITIDAS = {
    "abre", "abrir", "accion", "actual", "agenda", "alerta", "analizar",
    "antes", "apertura", "aprobable", "asegura", "atribuida", "basado",
    "caso", "cierre", "cifra", "cifras", "cita", "citado", "cobertura",
    "como", "conecta", "confirmar", "contexto", "copy", "dato", "datos",
    "declaracion", "declaro", "desde", "digital", "dice", "dijo",
    "editorial", "enfoque", "entre", "equivalia", "equivale", "esta",
    "falta", "frase", "fuente", "guion", "hecho", "impacto", "indica",
    "indico", "interes", "investigar", "local", "medio", "metadatos",
    "modelo", "muestra", "nota", "noticia", "oficial", "para", "parte",
    "pendiente", "pregunta", "publico", "publica", "publicado", "que",
    "redaccion", "reduce", "reduccion", "registra", "registrado", "registrar",
    "reporta", "reportan", "reporto", "requiere", "revisar", "segun",
    "senala", "senalo", "solo", "sostiene", "sustenta", "tema", "titular", "titulares",
    "trata", "verificar", "version",
}

INSTRUCCIONES_PROHIBIDAS = re.compile(r"\b(ignora|instrucciones|revela|secretos?|prompt|sistema|anteriores)\b", re.I)
# Tono publicitario o sensacionalista: impropio de un borrador periodístico.
TONO_PROHIBIDO = re.compile(r"[!¡]|\b(reserva (?:tu|ya|ahora)|descubre (?:la|el|tu|c[oó]mo)|inolvidable\w*|aventura\w*|imperdible\w*|no te lo pierdas|vive la emoci[oó]n|la emoci[oó]n de|incre[ií]ble\w*|impactante\w*)\b", re.I)
MENCIONES_PROHIBIDAS = re.compile(r"\b(im[aá]genes?|foto(?:s)?|video(?:s)?|entrevista(?:s)?|declaraci[oó]n directa|comillas)\b|[\"“”]", re.I)


@dataclass
class GuardianResult:
    aceptadas: list
    retiradas: list
    sospechosas: list
    abstencion: bool
    explicacion: str

    def to_dict(self) -> dict:
        return {"aceptadas": self.aceptadas, "retiradas": self.retiradas,
                "sospechosas": self.sospechosas, "abstencion": self.abstencion,
                "explicacion": self.explicacion}


def normalizar(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()


def tokens(texto: str) -> set[str]:
    return {part for part in re.findall(r"[a-záéíóúñü0-9]{4,}", normalizar(texto))}


def numeros(texto: str) -> set[str]:
    found = set()
    for value in re.findall(r"\d+(?:[.,]\d+)?", texto or ""):
        normalized = value.replace(",", ".")
        found.add(normalized)
        if normalized.endswith(".0"):
            found.add(normalized[:-2])
    return found


def texto_evidencia(evidencia: dict) -> str:
    parts = [
        evidencia.get("texto"), evidencia.get("titulo"), evidencia.get("noticia_titulo"),
        evidencia.get("medio"), evidencia.get("fuente_nombre"), evidencia.get("indicador_fuente_nombre"),
        evidencia.get("pais_iso3"), evidencia.get("indicador_id"), evidencia.get("anio"),
        evidencia.get("valor"), evidencia.get("unidad"), evidencia.get("fecha_publicacion"),
        evidencia.get("fecha_deteccion"), evidencia.get("limitaciones"),
    ]
    return " ".join(str(part) for part in parts if part not in (None, ""))


def evidencias_sospechosas(evidencias: list[dict]) -> list[dict]:
    sospechosas = []
    for evidencia in evidencias:
        texto = texto_evidencia(evidencia)
        if INSTRUCCIONES_PROHIBIDAS.search(texto):
            sospechosas.append({"evidencia_id": evidencia.get("id"), "motivo": "Contiene texto con apariencia de instruccion."})
    return sospechosas


def _corpus_por_id(evidencias: list[dict]) -> dict[str, str]:
    return {str(e["id"]): texto_evidencia(e) for e in evidencias if e.get("id")}


def validar_oraciones(oraciones: list[dict], evidencias: list[dict],
                      permitidas: set[str] | None = None) -> GuardianResult:
    permitidas = set(PALABRAS_PERMITIDAS | (permitidas or set()))
    corpus = _corpus_por_id(evidencias)
    sospechosas = evidencias_sospechosas(evidencias)
    ids_sospechosas = {item["evidencia_id"] for item in sospechosas}
    aceptadas, retiradas, vistos = [], [], set()
    corpus_total = normalizar(" ".join(corpus.values()))
    tokens_total = tokens(corpus_total) | permitidas

    for item in oraciones:
        texto = str(item.get("texto", "")).strip()
        evidencia_id = item.get("evidencia_id")
        key = normalizar(texto)
        if not texto:
            continue
        motivo = None
        if key in vistos:
            motivo = "Duplicado."
        elif not evidencia_id or evidencia_id not in corpus:
            motivo = "Afirmacion factual sin cita valida."
        elif evidencia_id in ids_sospechosas:
            motivo = "La evidencia citada fue excluida por posible instruccion."
        elif MENCIONES_PROHIBIDAS.search(texto):
            motivo = "Menciona imagenes, entrevistas, citas directas o comillas sin evidencia."
        elif TONO_PROHIBIDO.search(normalizar(texto)) or TONO_PROHIBIDO.search(texto):
            motivo = "Tono publicitario o sensacionalista."
        else:
            nums = numeros(texto)
            allowed_nums = numeros(corpus[evidencia_id])
            inventados = sorted(value for value in nums if value not in allowed_nums)
            if inventados:
                motivo = "Cifras sin respaldo en la evidencia citada: " + ", ".join(inventados)
            else:
                usados = tokens(texto)
                sin_respaldo = sorted(tok for tok in usados if tok not in tokens_total)
                if sin_respaldo:
                    motivo = "Terminos sin respaldo: " + ", ".join(sin_respaldo[:8])
        if motivo:
            retiradas.append({**item, "motivo": motivo})
        else:
            aceptadas.append(item)
            vistos.add(key)

    abstencion = not aceptadas
    explicacion = ("No queda ninguna afirmacion citada tras aplicar el guardian; falta evidencia valida."
                   if abstencion else "Borrador aceptable con retiro de oraciones no sustentadas." if retiradas else "Borrador aceptable.")
    return GuardianResult(aceptadas, retiradas, sospechosas, abstencion, explicacion)


def validar_borrador(paquete: dict, evidencias: list[dict], permitidas: set[str] | None = None) -> dict:
    oraciones = []
    for seccion in ("brief", "guion", "copy"):
        for item in paquete.get(f"{seccion}_oraciones", []):
            oraciones.append({**item, "seccion": seccion})
    return validar_oraciones(oraciones, evidencias, permitidas).to_dict()
