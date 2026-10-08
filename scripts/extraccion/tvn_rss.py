"""Lectura de capturas RSS de TVN sin copiar contenido protegido."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import xml.etree.ElementTree as ET

from .comun import id_noticia, iso_utc, normalizar_url

RSS_URL = "https://www.tvn-2.com/rss/"


def capturar(raw_dir, obtener, fecha_utc):
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = fecha_utc.replace("-", "").replace(":", "").replace("Z", "Z")
    path = raw_dir / f"tvn_rss_{stamp}.xml"
    with path.open("xb") as stream:
        stream.write(obtener(RSS_URL, pausa_min_s=0))
    return path


def fecha_pubdate(value):
    dt = parsedate_to_datetime(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return iso_utc(dt)


def filas_desde_archivos(raw_dir, fecha_extraccion, excluidos, vistos=None):
    vistos = vistos if vistos is not None else set()
    rows = []
    for path in sorted(Path(raw_dir).glob("*.xml")):
        root = ET.fromstring(path.read_bytes())
        for item in root.findall("./channel/item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or item.findtext("guid") or "").strip()
            normalized = normalizar_url(link)
            if not title or not link:
                excluidos.append({"fuente": "tvn_rss", "archivo": path.name, "url": link, "causa": "registro_incompleto"})
                continue
            if normalized in vistos:
                excluidos.append({"fuente": "tvn_rss", "archivo": path.name, "url": link, "causa": "duplicado_url_normalizada"})
                continue
            vistos.add(normalized)
            rows.append({
                "id_noticia": id_noticia(link),
                "titulo": title,
                "url": normalized,
                "medio": "TVN",
                "idioma": "es",
                "fecha_publicacion": fecha_pubdate(item.findtext("pubDate")) if item.findtext("pubDate") else "",
                "fecha_deteccion": "",
                "fecha_extraccion": fecha_extraccion,
                "tema": "sin_clasificar",
                "origen": "",
                "alcance_texto": "titular_metadatos",
            })
    return rows, vistos

