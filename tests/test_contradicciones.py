import csv
from pathlib import Path
import sqlite3
import unittest

import numpy as np

from scripts.importar_csv import run_import
from scripts.procesar_snapshot import process
from src.ia.contradicciones import detectar, extraer_cifras
from src.ia.guardian import validar_oraciones
from src.interfaz.app import case_detail, connect
from tests.helpers import temporary_directory

ROOT = Path(__file__).resolve().parents[1]
INDICADORES = ROOT / "tests/fixtures/csv/indicadores.csv"


def vectorizador_falso(textos, tipo="passage"):
    salida = []
    for texto in textos:
        low = texto.lower()
        vec = np.array([1, 0, 0, 0], dtype="float32") if "dona" in low or "equipos" in low else np.array([0, 1, 0, 0], dtype="float32")
        salida.append(vec)
    return np.vstack(salida).astype("float32")


class ContradiccionesTests(unittest.TestCase):
    def test_sintetico_dinero_incompatible_entre_medios(self):
        hallazgos = detectar([
            {"id": "SYN-1", "medio": "Crítica", "titulo": "SYN: EE.UU. dona $500 mil en equipos de emergencia"},
            {"id": "SYN-2", "medio": "TVN", "titulo": "SYN: EE.UU. dona $5 millones en equipos de emergencia"},
        ])
        self.assertEqual(len(hallazgos), 1)
        self.assertEqual(hallazgos[0]["clase"], "dinero")
        self.assertEqual({lado["medio"] for lado in hallazgos[0]["lados"]}, {"Crítica", "TVN"})

    def test_control_negativo_real_misma_cifra_normalizada(self):
        hallazgos = detectar([
            {"id": "N1", "medio": "Crítica", "titulo": "EE.UU. dona a Panamá equipos de emergencia valorados en $500 mil"},
            {"id": "N2", "medio": "TVN", "titulo": "EEUU dona a Panamá equipos por $500,000 para habilitar albergues"},
        ])
        self.assertEqual(hallazgos, [])

    def test_ignora_anos_marcadores_juego_y_ordinale(self):
        textos = [
            "Carnival Miracle inaugura temporada 2026-2027",
            "Dodgers 1-1 Bravos",
            "Juego 4 queda suspendido por lluvia",
            "El 3er informe queda pendiente",
        ]
        for texto in textos:
            self.assertEqual(extraer_cifras(texto), [])

    def test_fechas_y_magnitudes_de_titulares_reales(self):
        # Auditoría 2026-10-08 sobre el snapshot real: «7 de octubre» salía como conteo de «de»
        # y «sismo con 53 muertos» como magnitud 53.
        self.assertEqual(extraer_cifras("Resultados del sorteo de la lotería del miércoles 7 de octubre de 2026"), [])
        self.assertEqual(extraer_cifras("Ifarhu fija hasta el 14 de octubre para entregar boletín"), [])
        cifras = extraer_cifras("Un terremoto de 5.7 sacude la isla indonesia de Flores tras fuerte sismo con 53 muertos")
        self.assertEqual([(c["clase"], c["valor"]) for c in cifras], [("magnitud", 5.7), ("conteo", 53.0)])
        cifras = extraer_cifras("Terremoto de 7.4 en Colombia deja 289 muertos")
        self.assertEqual([(c["clase"], c["valor"]) for c in cifras], [("magnitud", 7.4), ("conteo", 289.0)])
        fechas = detectar([
            {"id": "SYN-F1", "medio": "TVN", "titulo": "Ifarhu fija hasta el 14 de octubre la entrega"},
            {"id": "SYN-F2", "medio": "Crítica", "titulo": "Ifarhu fija hasta el 7 de octubre la entrega"},
        ])
        self.assertEqual(fechas, [], "una fecha distinta no es una cifra en conflicto")

    def test_mismo_medio_no_es_contradiccion(self):
        hallazgos = detectar([
            {"id": "SYN-1", "medio": "TVN", "titulo": "SYN: donan $500 mil en equipos"},
            {"id": "SYN-2", "medio": "TVN", "titulo": "SYN: donan $5 millones en equipos"},
        ])
        self.assertEqual(hallazgos, [])

    def test_conteos_de_sustantivos_distintos_no_se_comparan(self):
        hallazgos = detectar([
            {"id": "SYN-1", "medio": "TVN", "titulo": "Canal contempla 220 tránsitos"},
            {"id": "SYN-2", "medio": "Crítica", "titulo": "Gobierno entrega 54 laptops"},
        ])
        self.assertEqual(hallazgos, [])

    def test_process_api_y_guardian_con_contradiccion(self):
        temp = temporary_directory()
        self.addCleanup(temp.cleanup)
        folder = Path(temp.name)
        noticias = folder / "noticias.csv"
        imported = folder / "imported.sqlite"
        derived = folder / "derived.sqlite"
        report = folder / "report.json"
        with noticias.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=[
                "id_noticia", "titulo", "url", "medio", "idioma", "fecha_publicacion",
                "fecha_deteccion", "fecha_extraccion", "tema", "origen", "alcance_texto",
            ])
            writer.writeheader()
            base = {
                "idioma": "es", "fecha_publicacion": "2024-06-01T10:00:00Z",
                "fecha_deteccion": "2024-06-01T10:30:00Z",
                "fecha_extraccion": "2024-06-02T12:00:00Z", "tema": "servicios_publicos",
                "origen": "SYN", "alcance_texto": "titular_metadatos",
            }
            writer.writerow({**base, "id_noticia": "SYN-N1",
                             "titulo": "SYN: EE.UU. dona a Panamá equipos de emergencia valorados en $500 mil",
                             "url": "https://example.invalid/syn-1", "medio": "Crítica"})
            writer.writerow({**base, "id_noticia": "SYN-N2",
                             "titulo": "SYN: EE.UU. dona a Panamá equipos de emergencia valorados en $5 millones",
                             "url": "https://example.invalid/syn-2", "medio": "TVN"})
        run_import(noticias, INDICADORES, imported, report, "SYN-SNAPSHOT", "test-v1", "2024-06-02T12:00:00Z")
        resultado = process(imported, derived, vectorizador=vectorizador_falso, umbral_grupo=.75)
        self.assertEqual(len(resultado["contradicciones"]), 1)
        caso_id = resultado["contradicciones"][0]["caso_id"]
        with connect(derived) as db:
            row = db.execute("SELECT estado_evidencia,preguntas_pendientes FROM casos WHERE id=?", (caso_id,)).fetchone()
            self.assertEqual(row["estado_evidencia"], "insuficiente")
            self.assertTrue(row["preguntas_pendientes"].startswith("Cifras incompatibles"))
            detalle = case_detail(db, caso_id)
            self.assertEqual(len(detalle["contradicciones"]), 1)
            evidencias = detalle["evidencias"]
        veredicto = validar_oraciones([
            {"texto": "Crítica reporta una donación de $500 mil.", "evidencia_id": evidencias[0]["id"], "tipo": "declaracion"},
        ], [{**evidencias[0], "cifras_conflicto": ["$500 mil", 500000]}])
        self.assertTrue(veredicto.abstencion)
        self.assertIn("cifra en conflicto entre medios", veredicto.retiradas[0]["motivo"])


if __name__ == "__main__":
    unittest.main()
