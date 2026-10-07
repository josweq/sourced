"""Normalización compartida para el snapshot de desarrollo."""
from datetime import datetime, timezone
import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def ahora_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso_utc(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalizar_url(url):
    parsed = urlsplit((url or "").strip())
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").lower()
    netloc = host
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    path = parsed.path or "/"
    if path.endswith("/amp"):
        path = path[:-4] or "/"
    if path.endswith("/"):
        path = path[:-1] or "/"
    query = urlencode([(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
                       if not k.lower().startswith("utm_")])
    return urlunsplit((scheme, netloc, path, query, ""))


def id_noticia(url):
    digest = hashlib.sha256(normalizar_url(url).encode("utf-8")).hexdigest()[:16]
    return "N-" + digest


def sha256_archivo(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def idioma_iso(value):
    if not value:
        return "es"
    text = value.strip().lower()
    return {
        "spanish": "es",
        "español": "es",
        "es": "es",
        "english": "en",
        "inglés": "en",
        "en": "en",
    }.get(text, text[:2])

