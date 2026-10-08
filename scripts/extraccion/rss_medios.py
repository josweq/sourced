"""Capturas RSS de varios medios panameños: solo titular y metadatos."""
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from .comun import id_noticia, normalizar_url
from .tvn_rss import fecha_pubdate

# Feeds públicos verificados el 2026-10-07. Los RSS conservan poco historial
# (TVN ~1 día), por eso las capturas se acumulan en data/raw/rss/<medio>/.
MEDIOS = {
    "tvn": ("TVN", "https://www.tvn-2.com/rss/"),
    "prensa": ("La Prensa", "https://www.prensa.com/arc/outboundfeeds/rss/"),
    "critica": ("Crítica", "https://www.critica.com.pa/rss.xml"),
    "panamaamerica": ("Panamá América", "https://www.panamaamerica.com.pa/rss.xml"),
    "ensegundos": ("En Segundos", "https://ensegundos.com.pa/feed/"),
}
CONDICIONES = "Solo titulares y metadatos del RSS público; no se copia description, contenido ni imágenes."


def capturar_todos(acumulado_dir, obtener, fecha_utc):
    """Guarda una captura nueva por medio; un medio caído no detiene a los demás."""
    stamp = fecha_utc.replace("-", "").replace(":", "")
    guardadas, fallidas = [], []
    for clave, (_nombre, url) in MEDIOS.items():
        destino = Path(acumulado_dir) / clave
        destino.mkdir(parents=True, exist_ok=True)
        try:
            payload = obtener(url, pausa_min_s=1)
            ET.fromstring(payload)  # descarta respuestas que no son XML
        except Exception as exc:  # noqa: BLE001 - se registra y se sigue
            fallidas.append({"medio": clave, "url": url, "error": str(exc)[:200]})
            continue
        path = destino / f"{clave}_{stamp}.xml"
        with path.open("xb") as stream:
            stream.write(payload)
        guardadas.append(str(path))
    return guardadas, fallidas


def copiar_acumulado(acumulado_dir, raw_rss_dir):
    """Copia al snapshot todas las capturas acumuladas para que sea reproducible."""
    total = 0
    for clave in MEDIOS:
        origen = Path(acumulado_dir) / clave
        if not origen.exists():
            continue
        destino = Path(raw_rss_dir) / clave
        destino.mkdir(parents=True, exist_ok=True)
        for path in sorted(origen.glob("*.xml")):
            shutil.copyfile(path, destino / path.name)
            total += 1
    return total


def filas_desde_capturas(raw_rss_dir, fecha_extraccion, excluidos, vistos=None):
    vistos = vistos if vistos is not None else set()
    filas = []
    for clave, (nombre, _url) in MEDIOS.items():
        for path in sorted((Path(raw_rss_dir) / clave).glob("*.xml")):
            try:
                root = ET.fromstring(path.read_bytes())
            except ET.ParseError:
                excluidos.append({"fuente": clave, "archivo": path.name, "causa": "xml_invalido"})
                continue
            for item in root.findall("./channel/item"):
                titulo = " ".join((item.findtext("title") or "").split())
                link = (item.findtext("link") or item.findtext("guid") or "").strip()
                if not titulo or not link.startswith("https://"):
                    excluidos.append({"fuente": clave, "archivo": path.name, "url": link, "causa": "registro_incompleto"})
                    continue
                normalizada = normalizar_url(link)
                if normalizada in vistos:
                    excluidos.append({"fuente": clave, "archivo": path.name, "url": link, "causa": "duplicado_url_normalizada"})
                    continue
                vistos.add(normalizada)
                pub = item.findtext("pubDate")
                try:
                    fecha_pub = fecha_pubdate(pub) if pub else ""
                except (TypeError, ValueError):
                    fecha_pub = ""
                filas.append({
                    "id_noticia": id_noticia(link),
                    "titulo": titulo,
                    "url": normalizada,
                    "medio": nombre,
                    "idioma": "es",
                    "fecha_publicacion": fecha_pub,
                    "fecha_deteccion": "",
                    "fecha_extraccion": fecha_extraccion,
                    "tema": "sin_clasificar",
                    "origen": "",
                    "alcance_texto": "titular_metadatos",
                })
    return filas, vistos


def fuentes(fecha_extraccion):
    return [{
        "id": f"SRC-RSS-{clave.upper()}",
        "nombre": f"{nombre} (RSS)",
        "familia": "noticias",
        "url": url,
        "condiciones": CONDICIONES,
        "fecha_extraccion": fecha_extraccion,
    } for clave, (nombre, url) in MEDIOS.items()]
