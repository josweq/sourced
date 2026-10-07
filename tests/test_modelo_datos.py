import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from scripts.modelo_datos import DEFAULT_FIXTURE, load_fixture, save_new


class DataContractTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(DEFAULT_FIXTURE.read_text(encoding="utf-8"))

    def load(self):
        db = load_fixture(self.data)
        self.addCleanup(db.close)
        return db

    def rejected(self):
        with self.assertRaises((ValueError, sqlite3.IntegrityError)):
            self.load()

    def test_null_is_not_zero_and_dates_are_separate(self):
        db = self.load()
        self.assertIsNone(db.execute("SELECT valor FROM indicadores WHERE id='SYN-I2'").fetchone()[0])
        row = db.execute("SELECT * FROM noticias WHERE id='SYN-N3'").fetchone()
        self.assertIsNone(row["fecha_publicacion"])
        self.assertIsNotNone(row["fecha_deteccion"])

    def test_publications_are_not_independent_sources(self):
        r = self.load().execute("SELECT * FROM procedencias_grupos WHERE grupo_id='SYN-G1'").fetchone()
        self.assertEqual((r["publicaciones"], r["procedencias_identificadas"], r["publicaciones_origen_desconocido"]), (3, 1, 1))

    def test_invalid_date(self):
        self.data["tables"]["noticias"][0]["fecha_publicacion"] = "2024-02-30T10:00:00Z"
        self.rejected()

    def test_utc_required(self):
        self.data["tables"]["noticias"][0]["fecha_publicacion"] = "2024-06-01T10:00:00"
        self.rejected()

    def test_cannot_mix_snapshots(self):
        other = copy.deepcopy(self.data["tables"]["snapshots"][0])
        other["id"] = "SYN-OTHER"
        self.data["tables"]["snapshots"].append(other)
        self.data["tables"]["noticias"][0]["snapshot_id"] = other["id"]
        self.rejected()

    def test_missing_evidence(self):
        self.data["tables"]["citas"][0]["evidencia_id"] = "SYN-NONEXISTENT"
        self.rejected()

    def test_fact_without_citation(self):
        self.data["tables"]["citas"] = []
        self.rejected()

    def test_contradiction_does_not_count_as_support(self):
        self.data["tables"]["citas"][0]["relacion"] = "contradice"
        self.rejected()

    def test_citation_must_belong_to_same_case(self):
        self.data["tables"]["citas"][0]["caso_id"] = "SYN-C3"
        self.rejected()

    def test_null_cannot_support_factual_value(self):
        self.data["tables"]["evidencias"][0]["indicador_registro_id"] = "SYN-I2"
        self.rejected()

    def test_invalid_locator(self):
        self.data["tables"]["evidencias"][0]["campo"] = "inventado"
        self.rejected()

    def test_duplicate_indicator_coordinate(self):
        row = copy.deepcopy(self.data["tables"]["indicadores"][0])
        row["id"] = "SYN-I-DUP"
        self.data["tables"]["indicadores"].append(row)
        self.rejected()

    def test_no_publication_state(self):
        self.data["tables"]["revisiones"][0]["estado"] = "publicado"
        self.rejected()

    def test_review_history_and_default_state(self):
        db = self.load()
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("UPDATE revisiones SET comentario='otro'")
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("DELETE FROM revisiones")
        self.assertEqual(db.execute("SELECT estado_revision FROM estado_casos WHERE id='SYN-C4'").fetchone()[0], "nuevo")

    def test_revision_sequence(self):
        self.data["tables"]["revisiones"][0]["secuencia"] = 2
        self.rejected()

    def test_demo_rejects_real_data(self):
        self.data["tables"]["snapshots"][0]["naturaleza"] = "real"
        self.rejected()

    def test_claim_present_in_draft(self):
        self.data["tables"]["afirmaciones"][0]["texto"] = "No existe en borrador"
        self.rejected()

    def test_priority_arithmetic(self):
        row = {"snapshot_id": "SYN-DEMO-001", "id": "SYN-P1", "caso_id": "SYN-C1",
               "reglas_version": "sugerida-v1", "componentes_json": json.dumps(dict.fromkeys("RIUNE", 1)),
               "pesos_json": json.dumps(dict(R=30, I=25, U=20, N=15, E=10)), "puntaje": 100,
               "explicacion": "Prueba sintética", "fecha_utc": "2024-06-02T12:00:00Z"}
        self.data["tables"]["priorizaciones"].append(row)
        self.assertEqual(self.load().execute("SELECT puntaje FROM priorizaciones").fetchone()[0], 100)
        row["puntaje"] = 99
        self.rejected()

    def test_brief_limit(self):
        self.data["tables"]["borradores"][0]["brief"] += " palabra" * 251
        self.rejected()

    def test_unknown_fields(self):
        self.data["tables"]["noticias"][0]["campo_desconocido"] = "no"
        self.rejected()

    def test_fixture_cannot_impersonate_real_url(self):
        self.data["tables"]["noticias"][0]["url"] = "https://www.tvn-2.com/noticia-falsa"
        self.rejected()

    def test_persistence_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            path = Path(folder) / "demo.sqlite"
            save_new(self.load(), path)
            db = sqlite3.connect(path)
            try:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM casos").fetchone()[0], 5)
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            finally:
                db.close()
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                save_new(self.load(), path)
            self.assertEqual(path.read_bytes(), before)

if __name__ == "__main__":
    unittest.main()
