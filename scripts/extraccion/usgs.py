"""Extractor USGS FDSN para eventos sísmicos regionales."""
import json
from urllib.parse import urlencode

BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def url_consulta(offset=1, limit=20000):
    params = {
        "format": "geojson",
        "starttime": "2024-01-01",
        "endtime": "2024-12-31",
        "minlatitude": "5",
        "maxlatitude": "12",
        "minlongitude": "-86",
        "maxlongitude": "-76",
        "minmagnitude": "3",
        "orderby": "time",
        "limit": str(limit),
        "offset": str(offset),
    }
    return BASE_URL + "?" + urlencode(params)


def simplificar(payload):
    data = json.loads(payload.decode("utf-8") if isinstance(payload, bytes) else payload)
    features = []
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        coords = (feature.get("geometry") or {}).get("coordinates") or [None, None, None]
        features.append({
            "type": "Feature",
            "id": feature.get("id"),
            "properties": {
                "mag": props.get("mag"),
                "time": props.get("time"),
                "updated": props.get("updated"),
                "place": props.get("place"),
                "status": props.get("status"),
                "url": props.get("url"),
            },
            "geometry": {
                "type": "Point",
                "coordinates": [coords[0], coords[1], coords[2]],
            },
        })
    return {"type": "FeatureCollection", "features": features}


def extraer(obtener):
    consultas = []
    respuestas = []
    features = []
    offset = 1
    limit = 20000
    while True:
        url = url_consulta(offset=offset, limit=limit)
        consultas.append(url)
        raw = obtener(url, pausa_min_s=0)
        respuestas.append(raw)
        data = json.loads(raw.decode("utf-8"))
        features.extend(simplificar(json.dumps(data)).get("features", []))
        metadata = data.get("metadata") or {}
        total = int(metadata.get("count") or len(features))
        if offset + limit > total:
            break
        offset += limit
    return {"type": "FeatureCollection", "features": features}, consultas, respuestas
