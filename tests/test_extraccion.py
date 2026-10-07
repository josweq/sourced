import csv
from email.message import Message
import json
from pathlib import Path
import shutil
import sqlite3
import unittest
import uuid
from urllib.error import HTTPError

from scripts.extraccion import banco_mundial, gdelt, red, tvn_rss, usgs
from scripts.extraccion.comun import id_noticia, normalizar_url, sha256_archivo
from scripts.extraccion.construir_snapshot import construir
from scripts.importar_csv import run_import

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/extraccion"


def test_dir():
    path = ROOT / "data/local" / f"test-extraccion-{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    return path


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        return False

    def read(self):
        return self.payload


def http_error(url, code, retry_after=None):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return HTTPError(url, code, "Too Many Requests", headers, None)


class ExtractionTests(unittest.TestCase):
    def test_red_429_respeta_retry_after(self):
        waits = []
        calls = []
        previous = red.urlopen
        try:
            def fake_urlopen(_request, timeout):
                calls.append(timeout)
                if len(calls) == 1:
                    raise http_error("https://example.test", 429, retry_after=3)
                return FakeResponse(b"ok")

            red.urlopen = fake_urlopen
            payload = red.obtener("https://example.test", espera=waits.append)
        finally:
            red.urlopen = previous
        self.assertEqual(payload, b"ok")
        self.assertEqual(waits, [3])

    def test_red_429_sin_cabecera_usa_espera_exponencial_larga(self):
        waits = []
        previous = red.urlopen
        try:
            red.urlopen = lambda _request, timeout: (_ for _ in ()).throw(http_error("https://example.test", 429))
            with self.assertRaises(RuntimeError):
                red.obtener("https://example.test", espera=waits.append)
        finally:
            red.urlopen = previous
        self.assertEqual(waits, [15, 30, 60])

    def test_banco_mundial_completa_cuadricula_explicita_con_nulos(self):
        raw = (FIXTURES / "banco_mundial_muestra.json").read_bytes()
        rows = banco_mundial.construir_filas({"NY.GDP.MKTP.KD.ZG": raw}, "2026-10-08T00:00:00Z")
        expected = len(banco_mundial.PAISES) * len(banco_mundial.INDICADORES) * len(banco_mundial.ANIOS)
        self.assertEqual(len(rows), expected)
        self.assertEqual(expected, 540)
        pan_2024 = [r for r in rows if r["pais_iso3"] == "PAN" and r["indicador_id"] == "NY.GDP.MKTP.KD.ZG" and r["anio"] == 2024][0]
        mex_pop_2024 = [r for r in rows if r["pais_iso3"] == "MEX" and r["indicador_id"] == "SP.POP.TOTL" and r["anio"] == 2024][0]
        self.assertNotEqual(pan_2024["valor"], "")
        self.assertEqual(mex_pop_2024["valor"], "")

    def test_id_estable_y_url_normalizada(self):
        original = "HTTPS://WWW.TVN-2.COM/noticia/amp?utm_source=x&b=1"
        normalized = "https://www.tvn-2.com/noticia?b=1"
        self.assertEqual(normalizar_url(original), normalized)
        self.assertEqual(id_noticia(original), id_noticia("https://www.tvn-2.com/noticia/?b=1"))
        self.assertTrue(id_noticia(original).startswith("N-"))
        self.assertEqual(len(id_noticia(original)), 18)

    def test_gdelt_seendate_es_deteccion_no_publicacion(self):
        excluidos = []
        rows, _vistos = gdelt.filas_desde_respuestas(
            [(FIXTURES / "gdelt_artlist_muestra.json").read_bytes()],
            "2026-10-08T00:00:00Z",
            excluidos,
        )
        self.assertEqual(rows[0]["fecha_publicacion"], "")
        self.assertEqual(rows[0]["fecha_deteccion"], "2026-10-01T22:30:00Z")
        self.assertEqual(rows[0]["idioma"], "es")

    def test_tvn_rss_no_copia_description_ni_media(self):
        excluidos = []
        rows, _vistos = tvn_rss.filas_desde_archivos(FIXTURES, "2026-10-08T00:00:00Z", excluidos)
        self.assertEqual(rows[0]["medio"], "TVN")
        self.assertEqual(rows[0]["fecha_publicacion"], "2026-10-07T21:59:32Z")
        text = json.dumps(rows, ensure_ascii=False)
        self.assertNotIn("description", text)
        self.assertNotIn("static.tvn-2.com", text)

    def test_usgs_simplifica_campos(self):
        payload = usgs.simplificar((FIXTURES / "usgs_muestra.geojson").read_bytes())
        feature = payload["features"][0]
        self.assertEqual(set(feature["properties"]), {"mag", "time", "updated", "place", "status", "url"})
        self.assertEqual(feature["geometry"]["coordinates"][0], -85.9299)

    def test_deduplica_tvn_y_gdelt_por_url_normalizada(self):
        tvn_url = "https://www.tvn-2.com/nacionales/canal-panama-carnival-miracle-inaugura_1_2264860.html"
        gdelt_payload = {"articles": [{
            "url": tvn_url + "?utm_source=gdelt",
            "title": "Duplicado",
            "seendate": "20261007T220000Z",
            "domain": "tvn-2.com",
            "language": "Spanish",
        }]}
        excluidos = []
        _tvn, vistos = tvn_rss.filas_desde_archivos(FIXTURES, "2026-10-08T00:00:00Z", excluidos)
        gdelt_rows, _vistos = gdelt.filas_desde_respuestas(
            [json.dumps(gdelt_payload).encode("utf-8")],
            "2026-10-08T00:00:00Z",
            excluidos,
            vistos,
        )
        self.assertEqual(gdelt_rows, [])
        self.assertEqual(excluidos[-1]["causa"], "duplicado_url_normalizada")

    def test_gdelt_consulta_fallida_no_aborta(self):
        previous_consultas = gdelt.CONSULTAS
        previous_ventanas = gdelt.ventanas
        try:
            gdelt.CONSULTAS = ("Panamá falla", "Panamá ok")
            gdelt.ventanas = lambda fecha_corte, dias: [(fecha_corte, fecha_corte)]

            def fake_obtener(url, pausa_min_s=0):
                if "falla" in url:
                    raise RuntimeError("HTTP 429 simulado")
                return (FIXTURES / "gdelt_artlist_muestra.json").read_bytes()

            rows, consultas, excluidos, cobertura, respuestas, fallidas = gdelt.extraer(
                fake_obtener,
                __import__("datetime").datetime(2026, 10, 8, tzinfo=__import__("datetime").timezone.utc),
                "2026-10-08T00:00:00Z",
                dias=90,
            )
        finally:
            gdelt.CONSULTAS = previous_consultas
            gdelt.ventanas = previous_ventanas
        self.assertEqual(len(consultas), 2)
        self.assertEqual(len(fallidas), 1)
        self.assertEqual(len(respuestas), 1)
        self.assertGreaterEqual(len(rows), 1)
        self.assertEqual(excluidos, [])
        self.assertEqual(cobertura["consultas_fallidas"], 1)

    def test_gdelt_respuesta_no_json_cuenta_como_fallida(self):
        previous_consultas = gdelt.CONSULTAS
        previous_ventanas = gdelt.ventanas
        try:
            gdelt.CONSULTAS = ("Panamá aviso",)
            gdelt.ventanas = lambda fecha_corte, dias: [(fecha_corte, fecha_corte)]
            rows, _consultas, _excluidos, cobertura, respuestas, fallidas = gdelt.extraer(
                lambda _url, pausa_min_s=0: b"Too Many Requests",
                __import__("datetime").datetime(2026, 10, 8, tzinfo=__import__("datetime").timezone.utc),
                "2026-10-08T00:00:00Z",
                dias=90,
            )
        finally:
            gdelt.CONSULTAS = previous_consultas
            gdelt.ventanas = previous_ventanas
        self.assertEqual(rows, [])
        self.assertEqual(respuestas, [])
        self.assertEqual(len(fallidas), 1)
        self.assertEqual(cobertura["noticias_gdelt"], 0)

    def test_snapshot_offline_genera_archivos_manifest_e_importa(self):
        folder = test_dir()
        try:
            from scripts.extraccion import construir_snapshot
            previous = construir_snapshot.ahora_utc
            construir_snapshot.ahora_utc = lambda: "2026-10-08T00:00:00Z"
            try:
                manifest = construir("test-v1", folder, offline=True)
            finally:
                construir_snapshot.ahora_utc = previous
            processed = folder / "test-v1" / "processed"
            expected = {"noticias.csv", "indicadores.csv", "eventos.geojson", "fuentes.json", "manifest.json", "excluidos.json"}
            self.assertEqual({p.name for p in processed.iterdir()}, expected)
            self.assertEqual(manifest["sha256"]["noticias.csv"], sha256_archivo(processed / "noticias.csv"))
            with (processed / "noticias.csv").open(encoding="utf-8", newline="") as stream:
                noticias = list(csv.DictReader(stream))
            self.assertGreaterEqual(len(noticias), 1)
            output, report = folder / "import.sqlite", folder / "report.json"
            result = run_import(processed / "noticias.csv", processed / "indicadores.csv",
                                output, report, "SNAPSHOT-DEV", "test-v1",
                                "2026-10-08T00:00:00Z", processed / "fuentes.json")
            self.assertEqual(result["archivos"]["noticias.csv"]["rechazadas"], 0)
            self.assertEqual(result["archivos"]["indicadores.csv"]["rechazadas"], 0)
            db = sqlite3.connect(output)
            try:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM fuentes WHERE url LIKE 'https://example.invalid/%'").fetchone()[0], 0)
            finally:
                db.close()
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_snapshot_no_sobrescribe_version(self):
        folder = test_dir()
        try:
            version_dir = folder / "test-v1"
            version_dir.mkdir()
            with self.assertRaises(FileExistsError):
                construir("test-v1", folder, offline=True)
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_snapshot_parcial_existente_no_bloquea_reintento(self):
        folder = test_dir()
        try:
            parcial = folder / "test-v1.parcial"
            parcial.mkdir()
            (parcial / "marca.txt").write_text("diagnóstico", encoding="utf-8")
            construir("test-v1", folder, offline=True)
            self.assertTrue((folder / "test-v1").exists())
            parciales_apartados = [path for path in folder.iterdir() if path.name.startswith("test-v1.parcial.")]
            self.assertEqual(len(parciales_apartados), 1)
            self.assertEqual((parciales_apartados[0] / "marca.txt").read_text(encoding="utf-8"), "diagnóstico")
            self.assertFalse((folder / "test-v1.parcial").exists())
        finally:
            shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
