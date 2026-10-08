from contextlib import closing
from pathlib import Path
import sqlite3
import unittest

import numpy as np

from scripts.importar_csv import run_import
from scripts.procesar_snapshot import process as process_ia
from src.ia.agrupacion import agrupar_semantico
from src.ia.clasificador import ClasificadorTema, clasificar_reglas, sin_clases_pequenas
from src.ia.embeddings import EXPECTED_DIM, cache_huggingface_existe, vectorizar
from src.ia.recuperacion import buscar
from tests.helpers import temporary_directory

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/csv"


def fake_vectorizer(textos, tipo="passage"):
    bases = {
        "economia": np.array([1, 0, 0, 0], dtype="float32"),
        "canal": np.array([0, 1, 0, 0], dtype="float32"),
        "turismo": np.array([0, 0, 1, 0], dtype="float32"),
        "agua": np.array([0, 0, 0, 1], dtype="float32"),
    }
    salida = []
    for texto in textos:
        low = texto.lower()
        vec = np.array([.05, .05, .05, .05], dtype="float32")
        for key, base in bases.items():
            if key in low or ("econ" in low and key == "economia"):
                vec = vec + base
        norm = np.linalg.norm(vec) or 1.0
        salida.append(vec / norm)
    return np.vstack(salida).astype("float32")


class CapaIATests(unittest.TestCase):
    def setUp(self):
        self.temp = temporary_directory()
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        self.imported = folder / "imported.sqlite"
        self.derived = folder / "ia.sqlite"
        run_import(FIXTURES / "noticias.csv", FIXTURES / "indicadores.csv",
                   self.imported, folder / "report.json", "IA-SNAPSHOT", "test-v1",
                   "2024-06-02T12:00:00Z")

    def test_clasificador_abstiene_por_umbral(self):
        rows = [
            {"titulo": "Economía local mejora", "etiqueta_humana": "economia"},
            {"titulo": "Precios y empleo suben", "etiqueta_humana": "economia"},
            {"titulo": "Canal registra tránsito", "etiqueta_humana": "logistica_canal"},
            {"titulo": "Buque llega al canal", "etiqueta_humana": "logistica_canal"},
        ]
        clf = ClasificadorTema.entrenar(rows, vectorizador=fake_vectorizer, umbral=.99)
        pred = clf.predecir(["Nota ambigua sin señales"])[0]
        self.assertEqual(pred["tema"], "sin_clasificar")
        self.assertEqual(pred["motivo"], "confianza baja")
        self.assertTrue(pred["vecinos"])

    def test_clase_con_pocos_ejemplos_no_impide_entrenar(self):
        # Caso real 2026-10-08: una sola etiqueta «logistica_canal» dejaba el modelo sin entrenar.
        rows = [{"titulo": f"t{i}", "etiqueta_humana": "economia"} for i in range(5)]
        rows += [{"titulo": "canal", "etiqueta_humana": "logistica_canal"}]
        quedan, excluidas = sin_clases_pequenas(rows)
        self.assertEqual(excluidas, {"logistica_canal": 1})
        self.assertEqual(len(quedan), 5)

    def test_reglas_tematicas_documentadas(self):
        tema, motivo = clasificar_reglas("Nueva ley y decreto regulan el transporte público")
        self.assertEqual(tema, "regulacion")
        self.assertIn("Palabras clave", motivo)

    def test_agrupacion_semantica_respeta_ventana_temporal(self):
        rows = [
            {"id": "A", "titulo": "Canal de Panamá registra tránsito", "fecha_publicacion": "2024-06-01T00:00:00Z"},
            {"id": "B", "titulo": "Canal reporta tránsito de buques", "fecha_publicacion": "2024-06-02T00:00:00Z"},
            {"id": "C", "titulo": "Canal reporta tránsito de buques", "fecha_publicacion": "2024-07-20T00:00:00Z"},
        ]
        groups = agrupar_semantico(rows, vectorizador=fake_vectorizer, umbral=.75, max_dias=7, umbral_muy_alto=1.01)
        self.assertEqual(sorted(len(g) for g in groups), [1, 2])

    def test_busqueda_hibrida_explica_motivo_y_abstiene(self):
        docs = [{"id": "1", "titulo": "Canal de Panamá registra tránsito"},
                {"id": "2", "titulo": "Hoteles esperan turistas"}]
        result = buscar("tránsito canal", docs, modo="hibrida", vectorizador=fake_vectorizer, umbral_semantico=.2)
        self.assertEqual(result["resultados"][0]["id"], "1")
        self.assertIn("Coincidió", result["resultados"][0]["motivo"])
        empty = buscar("sin relación", docs, modo="semantica", vectorizador=fake_vectorizer, umbral_semantico=1.01)
        self.assertTrue(empty["abstencion"])
        self.assertEqual(empty["resultados"], [])

    def test_cache_sqlite_no_recalcula(self):
        calls = {"n": 0}

        def encoder(prefijados):
            calls["n"] += 1
            return fake_vectorizer([p.split(": ", 1)[1] for p in prefijados])

        db = sqlite3.connect(":memory:")
        first = vectorizar(["Canal de Panamá"], db=db, encoder=encoder, modelo="fake")
        second = vectorizar(["Canal de Panamá"], db=db, encoder=encoder, modelo="fake")
        self.assertEqual(calls["n"], 1)
        np.testing.assert_allclose(first, second)
        db.close()

    def test_procesar_snapshot_crea_derivada_y_no_sobrescribe(self):
        result = process_ia(self.imported, self.derived, vectorizador=fake_vectorizer)
        self.assertEqual(result["reglas_version"], "ia-v1")
        self.assertTrue(self.derived.exists())
        with closing(sqlite3.connect(self.imported)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM casos").fetchone()[0], 0)
        with closing(sqlite3.connect(self.derived)) as db:
            self.assertGreater(db.execute("SELECT COUNT(*) FROM casos").fetchone()[0], 0)
            self.assertGreater(db.execute("SELECT COUNT(*) FROM ia_embeddings").fetchone()[0], 0)
        with self.assertRaises(FileExistsError):
            process_ia(self.imported, self.derived, vectorizador=fake_vectorizer)

    @unittest.skipUnless(cache_huggingface_existe(), "Modelo de embeddings no está en caché local")
    def test_modelo_real_dim_384_y_normalizado(self):
        vec = vectorizar(["prueba de dimensión"], tipo="passage")
        self.assertEqual(vec.shape, (1, EXPECTED_DIM))
        self.assertAlmostEqual(float(np.linalg.norm(vec[0])), 1.0, places=4)


if __name__ == "__main__":
    unittest.main()
