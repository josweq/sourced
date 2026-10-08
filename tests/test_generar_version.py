import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import threading
import unittest
from unittest.mock import patch

from scripts.modelo_datos import DEFAULT_FIXTURE, load_fixture, save_new
from src.editorial.criterios import construir_prompt_version, validar
from src.editorial.generar_version import generar_version
from src.ia.proveedores import ProviderUnavailable
from src.interfaz import app as interfaz_app
from src.interfaz.app import Handler
from tests.helpers import temporary_directory


EVIDENCIAS = [
    {"id": "EV1", "campo": "titulo", "noticia_titulo": "Canal de Panamá reduce calado máximo por sequía en el lago Gatún", "medio": "TVN", "alcance_texto": "titular_metadatos"},
    {"id": "EV2", "campo": "titulo", "noticia_titulo": "Navieras reportan demoras de hasta 10 días en tránsitos por el Canal", "medio": "Agencia", "alcance_texto": "titular_metadatos"},
]


def paquete(sensible=False):
    titulo = "Accidente deja heridos en la vía Interamericana" if sensible else "Caso de prueba"
    afirmacion = "TVN reporta en titular: Accidente deja heridos en la vía Interamericana." if sensible else "TVN reporta en titular: Canal de Panamá reduce calado máximo por sequía en el lago Gatún."
    evidencia_titulo = "Accidente deja heridos en la vía Interamericana" if sensible else EVIDENCIAS[0]["noticia_titulo"]
    evidencias = [{**EVIDENCIAS[0], "noticia_titulo": evidencia_titulo}, EVIDENCIAS[1]]
    return {
        "caso": {"id": "CASO-1", "titulo": titulo},
        "titulo": titulo,
        "preguntas_pendientes": "fuente primaria.",
        "alcance_texto": "titular_metadatos",
        "afirmaciones": [
            {"id": "AF1", "texto": afirmacion, "tipo": "declaracion", "evidencia_id": "EV1", "campo": "titulo", "cita_label": "Titular · TVN"},
            {"id": "AF2", "texto": "Agencia reporta en titular: Navieras reportan demoras de hasta 10 días en tránsitos por el Canal.", "tipo": "declaracion", "evidencia_id": "EV2", "campo": "titulo", "cita_label": "Titular · Agencia"},
        ],
        "evidencias": evidencias,
    }


def fake_provider(prompt, schema, timeout=0):
    datos = json.loads(prompt.split("DATOS, no instrucciones:\n", 1)[1])
    primera = datos["afirmaciones_citadas"][0]
    return {
        "oraciones": [
            {"texto": primera["texto"], "evidencia_id": primera["evidencia_id"]},
            {"texto": "La cifra sube a 999 millones este año.", "evidencia_id": primera["evidencia_id"]},
        ]
    }


class CriteriosPromptTests(unittest.TestCase):
    def test_prompt_incluye_solo_criterios_elegidos(self):
        criterios = validar({"formato": "vertical", "duracion_s": "", "palabras": 100, "tono": "cercano", "enfoque": "", "publico": ""})
        prompt = construir_prompt_version({"id": "C1", "titulo": "Caso"}, paquete()["afirmaciones"], criterios)
        self.assertIn("Formato: Reel / Short vertical", prompt)
        self.assertIn("Extensión objetivo: 100 palabras como máximo", prompt)
        self.assertIn("Tono: Cercano", prompt)
        self.assertNotIn("Duración objetivo", prompt)
        self.assertNotIn("Público:", prompt)

    def test_prompt_con_todo_libre_sigue_valido(self):
        criterios = validar({key: "" for key in ("formato", "duracion_s", "palabras", "tono", "enfoque", "publico", "enfasis")})
        prompt = construir_prompt_version({"id": "C1", "titulo": "Caso"}, paquete()["afirmaciones"], criterios)
        self.assertIn("afirmaciones_citadas", prompt)
        self.assertNotIn("Formato:", prompt)

    def test_valor_desconocido_falla(self):
        with self.assertRaises(ValueError):
            validar({"tono": "festivo"})


class GenerarVersionTests(unittest.TestCase):
    def test_guardian_retira_cifra_inventada_y_deja_citada(self):
        result = generar_version(paquete(), validar({"formato": "web"}), proveedor=fake_provider)
        self.assertTrue(result["oraciones"])
        self.assertTrue(any("Cifras sin respaldo" in item["motivo"] for item in result["retiradas"]))
        self.assertNotIn("999 millones", result["texto"])

    def test_objetivo_largo_no_rellena_y_declara_alcance(self):
        result = generar_version(paquete(), validar({"palabras": 1000}), proveedor=fake_provider)
        self.assertLess(result["palabras"], 700)
        self.assertIn("Con la evidencia disponible", result["alcance"])

    def test_tema_sensible_ajusta_tono_alegre(self):
        result = generar_version(paquete(sensible=True), validar({"tono": "alegre"}), proveedor=fake_provider)
        self.assertEqual(result["criterios_aplicados"]["tono"], "sobrio")
        self.assertIn("Tono ajustado a sobrio", " ".join(result["avisos"]))

    def test_ollama_no_disponible_usa_respaldo_determinista(self):
        def unavailable(prompt, schema, timeout=0):
            raise ProviderUnavailable("sin ollama")
        result = generar_version(paquete(), validar({"formato": "vertical", "duracion_s": 30}), proveedor=unavailable)
        self.assertIn("Generado sin modelo", " ".join(result["avisos"]))
        self.assertTrue(result["texto"])


class GenerarVersionApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = temporary_directory()
        self.addCleanup(self.temp.cleanup)
        self.path = self.temp.name + "/generar-api.sqlite"
        db = load_fixture(json.loads(DEFAULT_FIXTURE.read_text(encoding="utf-8")))
        save_new(db, self.path)
        db.close()
        Handler.db_path = self.path
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.thread.join, 1)
        self.addCleanup(self.server.shutdown)

    def request(self, body):
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        self.addCleanup(conn.close)
        conn.request("POST", "/api/borradores/SYN-B1/generar",
                     body=json.dumps(body).encode("utf-8"),
                     headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        return response.status, json.loads(response.read().decode("utf-8"))

    def test_api_generar_200_con_proveedor_falso(self):
        def version_fake(paquete_borrador, criterios):
            return generar_version(paquete_borrador, criterios, proveedor=fake_provider)
        with patch.object(interfaz_app, "generar_version", side_effect=version_fake):
            status, payload = self.request({"formato": "web", "tono": "sobrio"})
        self.assertEqual(status, 200)
        self.assertIn("prompt", payload)
        self.assertTrue(payload["oraciones"])

    def test_api_generar_400_por_criterio_desconocido(self):
        status, payload = self.request({"tono": "festivo"})
        self.assertEqual(status, 400)
        self.assertIn("Criterio inválido", payload["error"])


if __name__ == "__main__":
    unittest.main()
