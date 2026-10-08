"""Cliente HTTP mínimo e inyectable para los extractores."""
from datetime import datetime, timezone
from email.utils import formatdate, parsedate_to_datetime
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import http.client

# Algunos medios (La Prensa) responden con más de 100 cabeceras; el límite por defecto de http.client corta en 100.
http.client._MAXHEADERS = 1000

USER_AGENT = "Sourced-Snapshot-Dev/1.0 (+https://github.com/pixeltabletop/sourced)"


def _retry_after_s(headers):
    value = headers.get("Retry-After") if headers else None
    if not value:
        return None
    try:
        return max(0, int(value))
    except ValueError:
        pass
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max(0, (retry_at - datetime.now(timezone.utc)).total_seconds())


def obtener(url, *, pausa_min_s=0, reintentos=2, timeout=30, espera=time.sleep):
    """Devuelve bytes de una URL con pausas y reintentos acotados."""
    if pausa_min_s > 0:
        espera(pausa_min_s)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
        "Date": formatdate(usegmt=True),
    }
    last_error = None
    attempt = 0
    while True:
        try:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as exc:
            last_error = exc
            if exc.code in (429, 503):
                if attempt >= 3:
                    break
                retry_after = _retry_after_s(exc.headers)
                delay = retry_after if retry_after is not None else (15 * (2 ** attempt))
                espera(delay)
                attempt += 1
                continue
            if attempt >= reintentos:
                break
            espera(min(2 ** attempt, 5))
            attempt += 1
        except (URLError, TimeoutError) as exc:
            last_error = exc
            if attempt >= reintentos:
                break
            espera(min(2 ** attempt, 5))
            attempt += 1
    raise RuntimeError(f"No se pudo obtener {url}: {last_error}") from last_error
