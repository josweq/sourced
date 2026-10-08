import csv
import json
from pathlib import Path
import sqlite3
import unittest

from scripts.importar_csv import run_import
from tests.helpers import temporary_directory

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/csv"


class ImporterTests(unittest.TestCase):
    def test_valid_rows_load_and_bad_rows_quarantine(self):
        with temporary_directory() as folder:
            output, report = Path(folder) / "data.sqlite", Path(folder) / "report.json"
            result = run_import(FIXTURES / "noticias.csv", FIXTURES / "indicadores.csv",
                                output, report, "TEST-SNAPSHOT", "test-v1",
                                "2024-06-02T12:00:00Z")
            self.assertEqual(result["archivos"]["noticias.csv"], {"aceptadas": 3, "rechazadas": 3})
            self.assertEqual(result["archivos"]["indicadores.csv"], {"aceptadas": 2, "rechazadas": 2})
            self.assertEqual(len(result["errores"]), 5)
            db = sqlite3.connect(output)
            try:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM noticias").fetchone()[0], 3)
                self.assertIsNone(db.execute("SELECT fecha_publicacion FROM noticias WHERE id='N-002'").fetchone()[0])
                self.assertIsNone(db.execute("SELECT valor FROM indicadores WHERE anio=2024").fetchone()[0])
            finally:
                db.close()
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["errores"], result["errores"])

    def test_each_news_points_to_its_own_outlet_source(self):
        snapshot = ROOT / "data/snapshot-dev/real-20261007b/processed"
        with temporary_directory() as folder:
            output, report = Path(folder) / "data.sqlite", Path(folder) / "report.json"
            run_import(snapshot / "noticias.csv", snapshot / "indicadores.csv", output, report,
                       "TEST-REAL", "test-v1", "2026-10-08T00:08:55Z", snapshot / "fuentes.json")
            db = sqlite3.connect(output)
            try:
                pares = dict(db.execute("""SELECT n.medio, GROUP_CONCAT(DISTINCT f.nombre)
                  FROM noticias n JOIN fuentes f ON f.snapshot_id=n.snapshot_id AND f.id=n.fuente_id
                  GROUP BY n.medio""").fetchall())
            finally:
                db.close()
        self.assertEqual(pares["La Prensa"], "La Prensa (RSS)")
        self.assertEqual(pares["Crítica"], "Crítica (RSS)")
        self.assertEqual(pares["En Segundos"], "En Segundos (RSS)")
        self.assertEqual(pares["TVN"], "TVN (RSS)")

    def test_headers_are_exact(self):
        with temporary_directory() as folder:
            folder = Path(folder)
            broken = folder / "noticias.csv"
            broken.write_text("id_noticia,titulo\nX,T\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                run_import(broken, FIXTURES / "indicadores.csv", folder / "x.sqlite",
                           folder / "x.json", "TEST-SNAPSHOT", "v1",
                           "2024-06-02T12:00:00Z")

    def test_does_not_overwrite_outputs(self):
        with temporary_directory() as folder:
            folder = Path(folder)
            output, report = folder / "data.sqlite", folder / "report.json"
            output.write_text("preservar", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                run_import(FIXTURES / "noticias.csv", FIXTURES / "indicadores.csv",
                           output, report, "TEST-SNAPSHOT", "v1",
                           "2024-06-02T12:00:00Z")
            self.assertEqual(output.read_text(encoding="utf-8"), "preservar")


if __name__ == "__main__":
    unittest.main()
