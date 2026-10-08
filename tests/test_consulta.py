import sqlite3
import unittest

import numpy as np

from src.ia.consulta import _contenido, responder


def base():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
      CREATE TABLE indicadores (snapshot_id TEXT, id TEXT, fuente_id TEXT, pais_iso3 TEXT, indicador_id TEXT,
        anio INTEGER, valor REAL, unidad TEXT, fuente_url TEXT, fecha_extraccion TEXT, licencia TEXT);
      CREATE TABLE noticias (snapshot_id TEXT, id TEXT, fuente_id TEXT, titulo TEXT, url TEXT, medio TEXT,
        idioma TEXT, fecha_publicacion TEXT, fecha_deteccion TEXT, fecha_extraccion TEXT, tema TEXT,
        origen TEXT, alcance_texto TEXT, texto_disponible TEXT);
      CREATE TABLE grupo_noticias (snapshot_id TEXT, grupo_id TEXT, noticia_id TEXT, procedencia_id TEXT,
        justificacion_procedencia TEXT);
    """)
    for anio, valor in ((2023, 1.49), (2024, 0.69)):
        db.execute("INSERT INTO indicadores VALUES ('S', ?, 'BM', 'PAN', 'FP.CPI.TOTL.ZG', ?, ?, '% anual', "
                   "'https://api.worldbank.org/x', '2026-10-08T00:00:00Z', 'CC BY 4.0')", (f"IND-{anio}", anio, valor))
    noticias = [("N1", "EE.UU. dona a Panamá equipos de emergencia", "Crítica", "logistica_canal"),
                ("N2", "EEUU dona a Panamá equipos por $500,000", "TVN", "sin_clasificar"),
                ("N3", "Shakira prepara un cierre histórico en Madrid", "TVN", "sin_clasificar")]
    for nid, titulo, medio, tema in noticias:
        db.execute("INSERT INTO noticias VALUES ('S', ?, 'F', ?, ?, ?, 'es', '2026-10-07T12:00:00Z', NULL, "
                   "'2026-10-08T00:00:00Z', ?, '', 'titular_metadatos', NULL)",
                   (nid, titulo, f"https://ejemplo.pa/{nid}", medio, tema))
    for nid in ("N1", "N2"):
        db.execute("INSERT INTO grupo_noticias VALUES ('S', 'G1', ?, NULL, NULL)", (nid,))
    return db


def vectorizador_falso(similitudes):
    """Devuelve vectores cuyo producto con la consulta da las similitudes indicadas por titular."""
    def vec(textos, tipo="passage"):
        if tipo == "query":
            return np.array([[1.0, 0.0]], dtype="float32")
        out = []
        for t in textos:
            s = similitudes.get(t, 0.5)
            out.append([s, float(np.sqrt(max(0.0, 1 - s * s)))])
        return np.array(out, dtype="float32")
    return vec


class ConsultaTests(unittest.TestCase):
    def test_cifra_anual_se_cita_con_ano_unidad_y_aviso_de_no_actual(self):
        r = responder(base(), "¿Cuál es la inflación de Panamá hoy?")
        self.assertEqual(r["estado"], "respondida")
        self.assertIn("2024", r["afirmaciones"][0]["texto"])
        self.assertIn("no es una medición actual", r["afirmaciones"][0]["texto"])
        self.assertEqual(r["afirmaciones"][0]["cita"]["id"], "IND-2024")
        self.assertTrue(r["vacios"])

    def test_ano_inexistente_se_abstiene_sin_inventar(self):
        r = responder(base(), "inflación de Panamá en 2026")
        self.assertEqual(r["estado"], "abstencion")
        self.assertIn("No hay dato de 2026", r["respuesta"])
        self.assertEqual(r["afirmaciones"][0]["tipo"], "contexto")

    def test_sin_evidencia_se_abstiene(self):
        vec = vectorizador_falso({"Shakira prepara un cierre histórico en Madrid": 0.86})
        r = responder(base(), "receta de sancocho", vectorizador=vec)
        self.assertEqual(r["estado"], "abstencion")
        self.assertEqual(r["afirmaciones"], [])

    def test_anio_mes_y_palabras_de_tiempo_no_cuentan_como_coincidencia(self):
        # Casos reales del 2026-10-08: «turistas en septiembre de 2026» devolvía el titular de cruceros
        # «2026-2027» y «¿hubo sismos esta semana?» devolvía «Semana de la RSE».
        self.assertEqual(_contenido("turistas en septiembre de 2026"), {"turistas"})
        self.assertEqual(_contenido("¿hubo sismos esta semana?"), {"sismos"})
        vec = vectorizador_falso({"Shakira prepara un cierre histórico en Madrid": 0.86})
        r = responder(base(), "Shakira en septiembre de 2026", vectorizador=vec)
        self.assertEqual(r["estado"], "respondida", "la palabra de tema sí cuenta")

    def test_linea_base_lexica_responde_por_palabra_comun(self):
        # La línea base sin IA no usa embeddings: basta una palabra de contenido común.
        def sin_embeddings(textos, tipo="passage"):
            raise AssertionError("el modo léxico no debe vectorizar")
        r = responder(base(), "equipos donados", vectorizador=sin_embeddings, modo="lexico")
        self.assertEqual(r["estado"], "respondida")
        self.assertEqual(r["reglas"]["modelo"], "palabras-clave-v1")
        r = responder(base(), "receta de sancocho", vectorizador=sin_embeddings, modo="lexico")
        self.assertEqual(r["estado"], "abstencion")

    def test_el_anio_no_entra_en_la_busqueda_semantica(self):
        consultas = []
        base_vec = vectorizador_falso({})

        def vec(textos, tipo="passage"):
            if tipo == "query":
                consultas.extend(textos)
            return base_vec(textos, tipo)
        responder(base(), "sismos en 2024", vectorizador=vec)
        self.assertEqual(consultas, ["sismos en"])

    def test_respuesta_citada_cuenta_medios_del_evento(self):
        vec = vectorizador_falso({"EE.UU. dona a Panamá equipos de emergencia": 0.93,
                                  "EEUU dona a Panamá equipos por $500,000": 0.92})
        r = responder(base(), "donación de equipos de Estados Unidos", vectorizador=vec)
        self.assertEqual(r["estado"], "respondida")
        self.assertEqual(len(r["afirmaciones"]), 1, "un evento agrupado se cita una vez")
        self.assertEqual(r["afirmaciones"][0]["medios_del_evento"], ["Crítica", "TVN"])
        self.assertIn("titular/metadatos", r["afirmaciones"][0]["texto"])

    def test_entorno_logistico_da_contexto_sectorial_sin_puntaje_de_clientes(self):
        vec = vectorizador_falso({"EE.UU. dona a Panamá equipos de emergencia": 0.8})
        r = responder(base(), "¿Qué señales públicas del entorno logístico debo revisar?", vectorizador=vec)
        self.assertEqual(r["estado"], "contexto_sectorial")
        self.assertIn("no un puntaje de clientes", r["respuesta"])


if __name__ == "__main__":
    unittest.main()
