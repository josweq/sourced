from pathlib import Path
import unittest

from scripts.importar_csv import run_import
from scripts.procesar_agenda import process
from src.interfaz.app import connect, search_cases
from tests.helpers import temporary_directory

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/csv"


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = temporary_directory()
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        imported = folder / "imported.sqlite"
        self.agenda = folder / "agenda.sqlite"
        run_import(FIXTURES / "noticias.csv", FIXTURES / "indicadores.csv",
                   imported, folder / "report.json", "SEARCH-SNAPSHOT", "test-v1",
                   "2024-06-02T12:00:00Z")
        process(imported, self.agenda)

    def search(self, **filters):
        with connect(self.agenda) as db:
            return search_cases(db, **filters)

    def test_text_search_is_accent_insensitive_and_explained(self):
        result = self.search(query="tema económico")
        self.assertEqual(len(result["resultados"]), 1)
        self.assertEqual(result["resultados"][0]["coincidencias"], ["economico", "tema"])
        self.assertEqual(result["resultados"][0]["relevancia_textual"], 1.0)
        self.assertEqual(result["baseline"], "palabras-clave-v1")
        self.assertGreaterEqual(result["tiempo_ms"], 0)

    def test_topic_and_evidence_filters(self):
        tourism = self.search(topic="turismo", evidence_state="insuficiente")
        self.assertEqual(len(tourism["resultados"]), 1)
        self.assertEqual(tourism["resultados"][0]["tema"], "turismo")

    def test_medium_and_date_range_filter_same_publication(self):
        result = self.search(medium="Otro medio", date_from="2024-06-01", date_to="2024-06-01")
        self.assertEqual(len(result["resultados"]), 1)
        self.assertIn("Otro medio ficticio", result["resultados"][0]["medios"])

    def test_no_results_abstains_explicitly(self):
        result = self.search(query="canal interoceánico")
        self.assertEqual(result["resultados"], [])
        self.assertTrue(result["abstencion"])
        self.assertIn("No hay casos sustentados", result["motivo_abstencion"])

    def test_invalid_filters_are_rejected(self):
        with self.assertRaises(ValueError):
            self.search(topic="inventado")
        with self.assertRaises(ValueError):
            self.search(date_from="2024-02-30")

    def test_reversed_date_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "fecha inicial"):
            self.search(date_from="2024-06-02", date_to="2024-06-01")


if __name__ == "__main__":
    unittest.main()
