"""Deteccion determinista de cifras incompatibles entre titulares."""
from __future__ import annotations

import re
import unicodedata


NUM = r"(?:\d+(?:[.,]\d{3})*(?:[.,]\d+)?|\d+)"
MONEDA = r"(?:US\$|\$|B/\.?|d[oó]lares?|balboas?)"
MULT = r"(?:mil millones|millones?|mill[oó]n|mil|M)"
# Palabras que siguen a un número sin ser lo contado: fechas («7 de octubre»), artículos,
# preposiciones, meses y monedas (estas últimas ya se extraen como dinero).
NO_SUSTANTIVOS = {
    "de", "del", "en", "y", "al", "la", "las", "el", "los", "con", "por", "para", "sin", "que", "su", "sus",
    "este", "esta", "estos", "estas", "ese", "esa", "mas", "menos", "hasta", "desde", "entre", "sobre",
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "setiembre",
    "octubre", "noviembre", "diciembre",
    "dolar", "dolare", "balboa", "millon", "millone", "mil", "magnitud",
}
IGNORAR_CONTEXTO = re.compile(
    r"\b(?:juego|episodio|cap[ií]tulo|temporada)\s+\d+\b|\b\d+(?:er|do|ro|to|[oa])\b",
    re.I,
)


def _normalizar_texto(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()


def _valor_numero(raw: str) -> float:
    value = raw.strip()
    if "," in value and "." in value:
        last_comma = value.rfind(",")
        last_dot = value.rfind(".")
        if last_comma > last_dot:
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        parts = value.split(",")
        value = "".join(parts) if len(parts[-1]) == 3 and len(parts) > 1 else value.replace(",", ".")
    elif "." in value:
        parts = value.split(".")
        if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
            value = "".join(parts)
    return float(value)


def _multiplicador(raw: str | None) -> float:
    value = _normalizar_texto(raw or "")
    if value == "mil millones":
        return 1_000_000_000
    if value in {"millon", "millones", "m"}:
        return 1_000_000
    if value == "mil":
        return 1_000
    return 1


def _es_ignorable(texto: str, inicio: int, fin: int) -> bool:
    normal = _normalizar_texto(texto)
    candidato = normal[inicio:fin]
    antes = normal[max(0, inicio - 16):inicio]
    despues = normal[fin:fin + 16]
    contexto = normal[max(0, inicio - 16):fin + 16]
    if re.fullmatch(r"(?:19|20)\d{2}", candidato):
        return True
    if re.search(r"(?:19|20)\d{2}\s*[-/]\s*(?:19|20)\d{2}", contexto):
        return True
    if re.search(r"\b\d{1,2}:\d{2}\b", contexto):
        return True
    if re.search(r"\b\d{1,2}\s*[-]\s*\d{1,2}\b", contexto):
        return True
    if re.search(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", contexto):
        return True
    if re.search(r"(?:juego|episodio|capitulo|temporada)\s+$", antes):
        return True
    if re.match(r"^\s*(?:er|do|ro|to|[oa])\b", despues):
        return True
    return bool(IGNORAR_CONTEXTO.search(contexto) and re.fullmatch(r"\d+", candidato))


def _span_ocupado(span: tuple[int, int], ocupados: list[tuple[int, int]]) -> bool:
    return any(span[0] < fin and span[1] > inicio for inicio, fin in ocupados)


def _sustantivo(raw: str) -> str:
    value = _normalizar_texto(raw)
    value = re.sub(r"[^a-z0-9]+", "", value)
    for sufijo in ("es", "s"):
        if len(value) > 4 and value.endswith(sufijo):
            return value[:-len(sufijo)]
    return value


def _agregar(resultado: list[dict], ocupados: list[tuple[int, int]], clase: str,
             texto: str, valor: float, span: tuple[int, int], sustantivo: str | None = None):
    item = {"clase": clase, "texto_cifra": texto.strip(), "valor": valor}
    if sustantivo:
        item["sustantivo"] = sustantivo
    resultado.append(item)
    ocupados.append(span)


def extraer_cifras(titulo) -> list[dict]:
    """Extrae cifras comparables de un titular, ignorando marcadores, fechas y anos."""
    texto = str(titulo or "")
    cifras: list[dict] = []
    ocupados: list[tuple[int, int]] = []

    dinero_pats = [
        re.compile(rf"(?P<moneda>US\$|\$|B/\.?)\s*(?P<num>{NUM})(?:\s*(?P<mult>{MULT}))?", re.I),
        re.compile(rf"\b(?P<num>{NUM})\s*(?P<mult>{MULT})?\s*(?P<moneda>d[oó]lares?|balboas?)\b", re.I),
    ]
    for pat in dinero_pats:
        for m in pat.finditer(texto):
            if _span_ocupado(m.span(), ocupados) or _es_ignorable(texto, *m.span("num")):
                continue
            valor = _valor_numero(m.group("num")) * _multiplicador(m.groupdict().get("mult"))
            _agregar(cifras, ocupados, "dinero", m.group(0), valor, m.span())

    for m in re.finditer(rf"\b(?P<num>{NUM})\s*(?:%|por ciento)\b", texto, re.I):
        if _span_ocupado(m.span(), ocupados) or _es_ignorable(texto, *m.span("num")):
            continue
        _agregar(cifras, ocupados, "porcentaje", m.group(0), _valor_numero(m.group("num")), m.span())

    # Magnitud solo cuando el titular la nombra («magnitud 6,1», «sismo de 5.7», «terremoto de 7.4»)
    # y el valor es plausible; «sismo con 53 muertos» no es una magnitud.
    magnitud_pats = [
        re.compile(rf"\bmagnitud\s+(?:de\s+)?(?P<num>{NUM})\b", re.I),
        re.compile(rf"\b(?:sismo|terremoto|temblor)\w*\s+de\s+(?:magnitud\s+)?(?P<num>{NUM})\b", re.I),
    ]
    for pat in magnitud_pats:
        for m in pat.finditer(texto):
            if _span_ocupado(m.span(), ocupados) or _es_ignorable(texto, *m.span("num")):
                continue
            valor = _valor_numero(m.group("num"))
            if valor > 10:
                continue
            _agregar(cifras, ocupados, "magnitud", m.group(0), valor, m.span())

    for m in re.finditer(rf"\b(?P<num>{NUM})\s+(?P<noun>[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][\wÁÉÍÓÚÜÑáéíóúüñ-]*)\b", texto):
        if _span_ocupado(m.span(), ocupados) or _es_ignorable(texto, *m.span("num")):
            continue
        noun = _sustantivo(m.group("noun"))
        if noun in NO_SUSTANTIVOS or len(noun) < 3:
            continue
        valor = _valor_numero(m.group("num"))
        if valor != int(valor):  # un conteo es entero: «7.4 en Colombia» no lo es
            continue
        _agregar(cifras, ocupados, "conteo", m.group(0), valor, m.span(), noun)

    return cifras


def _evidencia_id(evidencia: dict) -> str:
    return str(evidencia.get("noticia_id") or evidencia.get("id") or evidencia.get("evidencia_id") or "")


def _titulo(evidencia: dict) -> str:
    return str(evidencia.get("titulo") or evidencia.get("noticia_titulo") or evidencia.get("texto") or "")


def _medio(evidencia: dict) -> str:
    return str(evidencia.get("medio") or evidencia.get("fuente_nombre") or "").strip()


def _clave(cifra: dict) -> tuple:
    if cifra["clase"] == "conteo":
        return cifra["clase"], cifra.get("sustantivo")
    return cifra["clase"], None


def _difieren(a: float, b: float) -> bool:
    base = max(abs(a), abs(b))
    if base == 0:
        return False
    return abs(a - b) / base > 0.05


def _lado(evidencia: dict, cifra: dict) -> dict:
    valor = cifra["valor"]
    if float(valor).is_integer():
        valor = int(valor)
    return {"medio": _medio(evidencia), "noticia_id": _evidencia_id(evidencia),
            "texto_cifra": cifra["texto_cifra"], "valor": valor}


def detectar(evidencias) -> list[dict]:
    """Compara cifras dentro de un caso; nunca decide cual medio tiene razon."""
    items = []
    for evidencia in evidencias:
        medio = _medio(evidencia)
        if not medio:
            continue
        for cifra in extraer_cifras(_titulo(evidencia)):
            items.append({"evidencia": evidencia, "cifra": cifra, "clave": _clave(cifra)})

    hallazgos = []
    vistos = set()
    for i, actual in enumerate(items):
        for otro in items[i + 1:]:
            if actual["clave"] != otro["clave"]:
                continue
            if _medio(actual["evidencia"]).casefold() == _medio(otro["evidencia"]).casefold():
                continue
            if not _difieren(float(actual["cifra"]["valor"]), float(otro["cifra"]["valor"])):
                continue
            lado_a = _lado(actual["evidencia"], actual["cifra"])
            lado_b = _lado(otro["evidencia"], otro["cifra"])
            key = tuple(sorted((lado_a["noticia_id"], lado_b["noticia_id"]))) + actual["clave"]
            if key in vistos:
                continue
            vistos.add(key)
            clase = actual["cifra"]["clase"]
            explicacion = (f"{lado_a['medio']} dice {lado_a['texto_cifra']}; "
                           f"{lado_b['medio']} dice {lado_b['texto_cifra']}: revisar con la fuente primaria "
                           "antes de usar cualquiera de las dos")
            hallazgos.append({"clase": clase, "lados": [lado_a, lado_b], "explicacion": explicacion})
    return hallazgos
