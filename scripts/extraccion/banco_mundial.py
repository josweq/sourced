"""Extractor del Banco Mundial para indicadores obligatorios."""
import json
from urllib.parse import urlencode

PAISES = ("PAN", "CRI", "COL", "DOM", "MEX", "GTM")
ANIOS = tuple(range(2010, 2025))
INDICADORES = {
    "NY.GDP.MKTP.KD.ZG": ("% anual", "PIB, crecimiento anual"),
    "FP.CPI.TOTL.ZG": ("% anual", "Inflación, precios al consumidor"),
    "SL.UEM.TOTL.ZS": ("% de la fuerza laboral", "Desempleo total"),
    "SP.POP.TOTL": ("personas", "Población total"),
    "IT.NET.USER.ZS": ("% de la población", "Personas que usan internet"),
    "NE.EXP.GNFS.ZS": ("% del PIB", "Exportaciones de bienes y servicios"),
}
LICENCIA = "CC BY 4.0 (verificar excepciones por indicador)"
BASE_URL = "https://api.worldbank.org/v2/country/{paises}/indicator/{indicador}"


def url_indicador(indicador, page=1, per_page=20000):
    params = {
        "format": "json",
        "date": "2010:2024",
        "page": str(page),
        "per_page": str(per_page),
    }
    return BASE_URL.format(paises=";".join(PAISES), indicador=indicador) + "?" + urlencode(params)


def leer_respuesta(raw):
    payload = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
    if not isinstance(payload, list) or len(payload) < 2:
        return {}, 1
    meta = payload[0] or {}
    rows = payload[1] or []
    values = {}
    for row in rows:
        iso3 = row.get("countryiso3code")
        indicator = (row.get("indicator") or {}).get("id")
        try:
            year = int(row.get("date"))
        except (TypeError, ValueError):
            continue
        if iso3 in PAISES and indicator in INDICADORES and year in ANIOS:
            values[(iso3, indicator, year)] = row.get("value")
    return values, int(meta.get("pages") or 1)


def consultar_indicador(indicador, obtener):
    valores = {}
    urls = []
    page = 1
    while True:
        url = url_indicador(indicador, page=page)
        urls.append(url)
        page_values, pages = leer_respuesta(obtener(url, pausa_min_s=0))
        valores.update(page_values)
        if page >= pages:
            break
        page += 1
    return valores, urls


def descargar(obtener):
    respuestas = {}
    consultas = []
    for indicador in INDICADORES:
        page = 1
        while True:
            url = url_indicador(indicador, page=page)
            consultas.append(url)
            raw = obtener(url, pausa_min_s=0)
            respuestas[f"{indicador}.page{page}"] = raw
            page_values, pages = leer_respuesta(raw)
            if page >= pages:
                break
            page += 1
    return respuestas, consultas


def construir_filas(respuestas_por_indicador, fecha_extraccion):
    filas = []
    urls = {ind: url_indicador(ind) for ind in INDICADORES}
    valores = {}
    for raw in respuestas_por_indicador.values():
        parsed, _pages = leer_respuesta(raw)
        valores.update(parsed)
    for pais in PAISES:
        for indicador, (unidad, _nombre) in INDICADORES.items():
            for anio in ANIOS:
                valor = valores.get((pais, indicador, anio))
                filas.append({
                    "pais_iso3": pais,
                    "indicador_id": indicador,
                    "anio": anio,
                    "valor": "" if valor is None else valor,
                    "unidad": unidad,
                    "fuente_url": urls[indicador],
                    "fecha_extraccion": fecha_extraccion,
                    "licencia": LICENCIA,
                })
    return filas


def extraer(obtener, fecha_extraccion):
    respuestas, consultas = descargar(obtener)
    return construir_filas(respuestas, fecha_extraccion), consultas
