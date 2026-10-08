"""Extractor GDELT DOC 2.0 para titulares y metadatos."""
from datetime import datetime, timedelta, timezone
import json
from json import JSONDecodeError
from urllib.parse import urlencode, urlsplit

from .comun import idioma_iso, id_noticia, iso_utc, normalizar_url

BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
CONSULTAS = (
    "Panamá",
    "Panamá economía",
    "Panamá Canal logística",
    "Panamá turismo",
    "Panamá servicios públicos",
    "Panamá eventos naturales",
    "Panamá regulación",
    "domain:tvn-2.com Panamá",
)


def gdelt_datetime(dt):
    return dt.strftime("%Y%m%d%H%M%S")


def parse_seendate(value):
    return iso_utc(datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc))


def dominio(url):
    return (urlsplit(url).hostname or "").lower()


def ventanas(fecha_corte, dias, tamano=7):
    end = fecha_corte
    start_limit = fecha_corte - timedelta(days=dias)
    result = []
    while end > start_limit:
        start = max(start_limit, end - timedelta(days=tamano))
        result.append((start, end))
        end = start
    return result


def url_consulta(query, start, end):
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": "250",
        "startdatetime": gdelt_datetime(start),
        "enddatetime": gdelt_datetime(end),
    }
    return BASE_URL + "?" + urlencode(params)


def filas_desde_respuestas(respuestas, fecha_extraccion, excluidos, vistos=None):
    vistos = vistos if vistos is not None else set()
    filas = []
    for raw in respuestas:
        data = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
        for article in data.get("articles", []):
            url = article.get("url") or ""
            titulo = (article.get("title") or "").strip()
            normalized = normalizar_url(url)
            if not url or not titulo:
                excluidos.append({"fuente": "gdelt", "url": url, "causa": "registro_incompleto"})
                continue
            if normalized in vistos:
                excluidos.append({"fuente": "gdelt", "url": url, "causa": "duplicado_url_normalizada"})
                continue
            vistos.add(normalized)
            filas.append({
                "id_noticia": id_noticia(url),
                "titulo": titulo,
                "url": normalized,
                "medio": (article.get("domain") or dominio(url)),
                "idioma": idioma_iso(article.get("language")),
                "fecha_publicacion": "",
                "fecha_deteccion": parse_seendate(article["seendate"]) if article.get("seendate") else "",
                "fecha_extraccion": fecha_extraccion,
                "tema": "sin_clasificar",
                "origen": "",
                "alcance_texto": "titular_metadatos",
            })
    return filas, vistos


def extraer(obtener, fecha_corte, fecha_extraccion, dias=30):
    consultas = []
    respuestas = []
    consultas_fallidas = []
    cobertura = {"dias_solicitados": dias, "dias_efectivos": dias}

    def consultar(url):
        consultas.append(url)
        try:
            raw = obtener(url, pausa_min_s=6)
            data = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
        except (RuntimeError, JSONDecodeError, UnicodeDecodeError) as exc:
            consultas_fallidas.append({"url": url, "error": str(exc)})
            return
        if not isinstance(data, dict):
            consultas_fallidas.append({"url": url, "error": "Respuesta JSON no es un objeto GDELT ArtList."})
            return
        respuestas.append(raw)

    for query in CONSULTAS:
        for start, end in ventanas(fecha_corte, dias):
            url = url_consulta(query, start, end)
            consultar(url)
    excluidos = []
    filas, _vistos = filas_desde_respuestas(respuestas, fecha_extraccion, excluidos)
    if len(filas) < 100 and dias < 90:
        cobertura["dias_efectivos"] = 90
        for query in CONSULTAS:
            for start, end in ventanas(fecha_corte - timedelta(days=dias), 90 - dias):
                url = url_consulta(query, start, end)
                consultar(url)
        excluidos = []
        filas, _vistos = filas_desde_respuestas(respuestas, fecha_extraccion, excluidos)
    cobertura["consultas_exitosas"] = len(respuestas)
    cobertura["consultas_fallidas"] = len(consultas_fallidas)
    cobertura["noticias_gdelt"] = len(filas)
    return filas, consultas, excluidos, cobertura, respuestas, consultas_fallidas
