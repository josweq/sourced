import json
from contextlib import closing
from pathlib import Path
import sqlite3
import unittest

from scripts.importar_csv import run_import
from scripts.procesar_agenda import group_news, process, similarity, tokens
from src.interfaz.app import case_detail, connect, list_cases
from tests.helpers import temporary_directory

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/csv"


class AgendaTests(unittest.TestCase):
    def setUp(self):
        self.temp = temporary_directory()
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        self.imported = folder / "imported.sqlite"
        self.agenda = folder / "agenda.sqlite"
        run_import(FIXTURES / "noticias.csv", FIXTURES / "indicadores.csv",
                   self.imported, folder / "report.json", "TEST-SNAPSHOT", "test-v1",
                   "2024-06-02T12:00:00Z")

    def test_token_similarity_ignores_accents_and_marker(self):
        self.assertGreaterEqual(similarity(tokens("[SINTÉTICO] Tema económico"),
                                           tokens("Tema economico actualización")), .55)

    def test_pipeline_groups_duplicates_and_ranks_cases(self):
        result = process(self.imported, self.agenda)
        self.assertEqual(result["casos_creados"], 2)
        grouped = next(item for item in result["casos"] if len(item["miembros"]) == 2)
        self.assertEqual(grouped["procedencias_identificadas"], 1)
        self.assertGreater(grouped["puntaje"], 0)
        with connect(self.agenda) as db:
            cases = list_cases(db)
            self.assertEqual(len(cases), 2)
            self.assertGreaterEqual(cases[0]["puntaje"], cases[1]["puntaje"])
            self.assertEqual(cases[0]["reglas_version"], "baseline-titulos-v1")
            detail = case_detail(db, grouped["caso_id"])
            self.assertEqual(len(detail["evidencias"]), 2)
            self.assertEqual(detail["agrupacion"]["publicaciones"], 2)
            self.assertEqual(detail["agrupacion"]["procedencias_identificadas"], 1)

    def test_output_is_new_and_input_remains_without_cases(self):
        process(self.imported, self.agenda)
        with closing(sqlite3.connect(self.imported)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM casos").fetchone()[0], 0)
        with self.assertRaises(FileExistsError):
            process(self.imported, self.agenda)

    def test_no_automatic_indicator_relation(self):
        process(self.imported, self.agenda)
        with closing(sqlite3.connect(self.agenda)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM evidencias WHERE indicador_registro_id IS NOT NULL").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
