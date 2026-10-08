"""CLI para construir el snapshot de desarrollo reproducible."""
import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from scripts.extraccion import banco_mundial, gdelt, rss_medios, tvn_rss, usgs
    from scripts.extraccion.comun import ahora_utc, sha256_archivo
    from scripts.extraccion.red import obtener as obtener_red
else:
    from . import banco_mundial, gdelt, rss_medios, tvn_rss, usgs
    from .comun import ahora_utc, sha256_archivo
    from .red import obtener as obtener_red

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/extraccion"
NEWS_FIELDS = (
    "id_noticia", "titulo", "url", "medio", "idioma", "fecha_publicacion",
    "fecha_deteccion", "fecha_extraccion", "tema", "origen", "alcance_texto",
)
INDICATOR_FIELDS = (
    "pais_iso3", "indicador_id", "anio", "valor", "unidad", "fuente_url",
    "fecha_extraccion", "licencia",
)


def escribir_csv(path, fields, rows):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def escribir_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def preparar_raw_offline(raw):
    raw.mkdir(parents=True, exist_ok=False)
    (raw / "banco_mundial").mkdir()
    (raw / "gdelt").mkdir()
    (raw / "usgs").mkdir()
    (raw / "tvn_rss").mkdir()
    shutil.copyfile(FIXTURES / "banco_mundial_muestra.json",
                    raw / "banco_mundial" / "NY.GDP.MKTP.KD.ZG.json")
    shutil.copyfile(FIXTURES / "gdelt_artlist_muestra.json",
                    raw / "gdelt" / "artlist_muestra.json")
    shutil.copyfile(FIXTURES / "usgs_muestra.geojson",
                    raw / "usgs" / "eventos.geojson")
    shutil.copyfile(FIXTURES / "tvn_rss_muestra.xml",
                    raw / "tvn_rss" / "tvn_rss_muestra.xml")


def acumulado_rss():
    return Path(os.environ.get("LUPA_RSS_ACUMULADO") or Path(__file__).resolve().parents[2] / "data" / "raw" / "rss")


def cargar_raw(raw, fecha_extraccion):
    respuestas_bm = {path.stem: path.read_bytes() for path in (raw / "banco_mundial").glob("*.json")}
    indicadores = banco_mundial.construir_filas(respuestas_bm, fecha_extraccion)
    excluidos = []
    noticias_tvn, vistos = tvn_rss.filas_desde_archivos(raw / "tvn_rss", fecha_extraccion, excluidos)
    noticias_rss, vistos = rss_medios.filas_desde_capturas(raw / "rss", fecha_extraccion, excluidos, vistos)
    noticias_tvn = noticias_tvn + noticias_rss
    respuestas_gdelt = [path.read_bytes() for path in sorted((raw / "gdelt").glob("*.json"))]
    noticias_gdelt, vistos = gdelt.filas_desde_respuestas(respuestas_gdelt, fecha_extraccion, excluidos, vistos)
    usgs_files = sorted((raw / "usgs").glob("*.geojson"))
    eventos = usgs.simplificar(usgs_files[0].read_bytes()) if usgs_files else {"type": "FeatureCollection", "features": []}
    return noticias_tvn + noticias_gdelt, indicadores, eventos, excluidos


def fuentes(fecha_extraccion):
    return rss_medios.fuentes(fecha_extraccion) + [
        {
            "id": "SRC-TVN-RSS",
            "nombre": "TVN RSS capturado",
            "familia": "noticias",
            "url": tvn_rss.RSS_URL,
            "condiciones": "Solo titulares y metadatos; no se copia description ni media:content.",
            "fecha_extraccion": fecha_extraccion,
        },
        {
            "id": "SRC-GDELT",
            "nombre": "GDELT DOC 2.0",
            "familia": "noticias",
            "url": gdelt.BASE_URL,
            "condiciones": "Metadatos de ArtList; seendate es fecha de detección, no publicación.",
            "fecha_extraccion": fecha_extraccion,
        },
        {
            "id": "SRC-BANCO-MUNDIAL",
            "nombre": "Banco Mundial API v2",
            "familia": "indicadores",
            "url": "https://api.worldbank.org/v2/",
            "condiciones": banco_mundial.LICENCIA,
            "fecha_extraccion": fecha_extraccion,
        },
    ]


def _marca_utc():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _apartar_parcial_existente(parcial):
    if not parcial.exists():
        return None
    destino = parcial.with_name(f"{parcial.name}.{_marca_utc()}")
    index = 1
    while destino.exists():
        destino = parcial.with_name(f"{parcial.name}.{_marca_utc()}.{index}")
        index += 1
    parcial.rename(destino)
    return destino


def construir(version, salida, dias=30, offline=False, capturar=False, obtener=obtener_red, sin_gdelt=False):
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    final = salida / version
    parcial = salida / f"{version}.parcial"
    if final.exists():
        raise FileExistsError(f"La versión ya existe y no se sobrescribe: {final}")
    _apartar_parcial_existente(parcial)

    base = parcial
    processed = base / "processed"
    raw = base / "raw"
    fecha_extraccion = ahora_utc()
    fecha_corte = datetime.now(timezone.utc).replace(microsecond=0)
    consultas = []
    consultas_fallidas = []
    cobertura = {"tvn_rss": "capturas disponibles en raw/tvn_rss", "gdelt": {"dias_efectivos": dias}}
    if offline:
        preparar_raw_offline(raw)
        noticias, indicadores, eventos, excluidos = cargar_raw(raw, fecha_extraccion)
        consultas.extend([
            banco_mundial.url_indicador(ind) for ind in banco_mundial.INDICADORES
        ])
        consultas.append(usgs.url_consulta())
        consultas.append("fixtures locales de GDELT y RSS; sin red")
    else:
        raw.mkdir(parents=True)
        if capturar:
            _guardadas, rss_fallidas = rss_medios.capturar_todos(acumulado_rss(), obtener, fecha_extraccion)
            consultas_fallidas.extend(rss_fallidas)
        consultas.extend(url for _nombre, url in rss_medios.MEDIOS.values())
        cobertura["rss_medios"] = {"capturas_copiadas": rss_medios.copiar_acumulado(acumulado_rss(), raw / "rss")}
        (raw / "banco_mundial").mkdir(parents=True)
        bm_raw, bm_urls = banco_mundial.descargar(obtener)
        for name, payload in bm_raw.items():
            (raw / "banco_mundial" / f"{name}.json").write_bytes(payload)
        indicadores = banco_mundial.construir_filas(bm_raw, fecha_extraccion)
        consultas.extend(bm_urls)
        if sin_gdelt:
            excluidos, gdelt_raw = [], []
            cobertura["gdelt"] = {"omitido": "GDELT respondió HTTP 429 a todas las consultas el 2026-10-07; se omite con --sin-gdelt"}
        else:
            _noticias_gdelt, gdelt_urls, excluidos, gdelt_cobertura, gdelt_raw, gdelt_fallidas = gdelt.extraer(
                obtener, fecha_corte, fecha_extraccion, dias=dias
            )
            consultas_fallidas.extend(gdelt_fallidas)
            consultas.extend(gdelt_urls)
            cobertura["gdelt"] = gdelt_cobertura
        eventos, usgs_urls, usgs_raw = usgs.extraer(obtener)
        consultas.extend(usgs_urls)
        (raw / "usgs").mkdir(parents=True)
        for index, payload in enumerate(usgs_raw, start=1):
            (raw / "usgs" / f"eventos_{index:03d}.geojson").write_bytes(payload)
        (raw / "gdelt").mkdir(parents=True)
        for index, payload in enumerate(gdelt_raw, start=1):
            (raw / "gdelt" / f"respuesta_{index:03d}.json").write_bytes(payload)
        noticias_tvn, vistos = rss_medios.filas_desde_capturas(raw / "rss", fecha_extraccion, excluidos)
        noticias_gdelt, _vistos = gdelt.filas_desde_respuestas(gdelt_raw, fecha_extraccion, excluidos, vistos)
        cobertura["gdelt"]["declara_sin_aportes"] = len(noticias_gdelt) == 0
        noticias = noticias_tvn + noticias_gdelt
    processed.mkdir()
    escribir_csv(processed / "noticias.csv", NEWS_FIELDS, noticias)
    escribir_csv(processed / "indicadores.csv", INDICATOR_FIELDS, indicadores)
    escribir_json(processed / "eventos.geojson", eventos)
    escribir_json(processed / "fuentes.json", fuentes(fecha_extraccion))
    escribir_json(processed / "excluidos.json", excluidos)
    conteos = {
        "noticias.csv": len(noticias),
        "indicadores.csv": len(indicadores),
        "eventos.geojson": len(eventos.get("features", [])),
        "fuentes.json": len(fuentes(fecha_extraccion)),
        "excluidos.json": len(excluidos),
    }
    hashes = {path.name: sha256_archivo(path) for path in processed.iterdir() if path.name != "manifest.json"}
    manifest = {
        "version": version,
        "fecha_corte_utc": fecha_extraccion,
        "consultas": consultas,
        "consultas_fallidas": consultas_fallidas,
        "conteos": conteos,
        "condiciones_por_fuente": {item["id"]: item["condiciones"] for item in fuentes(fecha_extraccion)},
        "sha256": hashes,
        "transformaciones": [
            "Normalización de URL: host en minúsculas, sin utm_*, sin /amp ni barra final.",
            "ID estable N- con 16 hex de SHA-256 de URL normalizada.",
            "RSS de TVN, La Prensa, Crítica, Panamá América y En Segundos: solo titular y metadatos; no se copia description ni media:content.",
            "GDELT seendate se registra como fecha_deteccion; fecha_publicacion queda vacía.",
            "Las consultas fallidas de GDELT se registran y no abortan el snapshot completo.",
            "Banco Mundial completa la cuadrícula explícita 6 países x 6 indicadores x 15 años; ausencias como valor vacío, nunca cero.",
            "Filtro temporal [2024-01-01, 2025-10-01) no aplicado, pendiente de la organización.",
        ],
        "cobertura_temporal_efectiva": cobertura,
        "nota_cuadricula": "Los parámetros explícitos producen 540 combinaciones; no se inventan combinaciones para llegar a 1.350.",
    }
    escribir_json(processed / "manifest.json", manifest)
    parcial.rename(final)
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Construir snapshot de desarrollo reproducible.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--salida", type=Path, default=Path("data/snapshot-dev"))
    parser.add_argument("--dias", type=int, default=30)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--capturar", action="store_true")
    parser.add_argument("--sin-gdelt", action="store_true", help="Omite GDELT (por ejemplo, si responde 429).")
    args = parser.parse_args()
    print(json.dumps(construir(args.version, args.salida, args.dias, args.offline, args.capturar, sin_gdelt=args.sin_gdelt),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
