import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import threading
import unittest

from scripts.modelo_datos import DEFAULT_FIXTURE, load_fixture, save_new
from src.editorial.formatos import adaptar
from src.interfaz.app import Handler
from tests.helpers import temporary_directory


EVIDENCIAS = [
    {"id": "EV1", "campo": "titulo", "noticia_titulo": "Canal de Panamá reduce calado máximo por sequía en el lago Gatún", "medio": "TVN", "alcance_texto": "titular_metadatos"},
    {"id": "EV2", "campo": "titulo", "noticia_titulo": "Navieras reportan demoras de hasta 10 días en tránsitos por el Canal", "medio": "Agencia", "alcance_texto": "titular_metadatos"},
    {"id": "EV3", "campo": "valor", "indicador_id": "NE.EXP.GNFS.ZS", "pais_iso3": "PAN", "anio": 2023, "valor": 41.3, "unidad": "% del PIB", "indicador_fuente_nombre": "Banco Mundial"},
]


def paquete(con_indicador=True):
    afirmaciones = [
        {"id": "AF1", "texto": "TVN reporta en titular: Canal de Panamá reduce calado máximo por sequía en el lago Gatún.", "tipo": "declaracion", "evidencia_id": "EV1", "campo": "titulo"},
        {"id": "AF2", "texto": "Agencia reporta en titular: Navieras reportan demoras de hasta 10 días en tránsitos por el Canal.", "tipo": "declaracion", "evidencia_id": "EV2", "campo": "titulo"},
    ]
    evidencias = EVIDENCIAS[:2]
    if con_indicador:
        afirmaciones.append({"id": "AF3", "texto": "El indicador NE.EXP.GNFS.ZS para PAN en 2023 registra 41.3 % del PIB.", "tipo": "hecho", "evidencia_id": "EV3", "campo": "valor"})
        evidencias = EVIDENCIAS
    return {
        "titulo": "Caso de prueba",
        "enfoque": "Revisar evidencia.",
        "brief": "",
        "guion": "",
        "copy": "",
        "preguntas": ["¿Cuál es la fuente primaria?", "¿Qué dato falta?", "¿Qué alcance tiene?"],
        "preguntas_pendientes": "fuente primaria, contexto y alcance antes de publicar.",
        "alcance_texto": "titular_metadatos",
        "afirmaciones": afirmaciones,
        "evidencias": evidencias,
    }


class FormatosTests(unittest.TestCase):
    def test_cada_formato_devuelve_oraciones_citadas(self):
        for formato in ("tv", "radio", "vertical", "web", "alerta"):
            with self.subTest(formato=formato):
                result = adaptar(paquete(), formato)
                self.assertTrue(result["avisos"])
                self.assertTrue(result["oraciones"])
                self.assertFalse([o for o in result["oraciones"] if not o.get("evidencia_id") or not o.get("campo")])

    def test_duracion_recorta_afirmaciones(self):
        largo = adaptar(paquete(), "tv", duracion_s=60)
        corto = adaptar(paquete(), "tv", duracion_s=3)
        self.assertLess(len(corto["oraciones"]), len(largo["oraciones"]))
        self.assertTrue(corto["recortado"])

    def test_enfasis_dato_con_y_sin_indicador(self):
        con = adaptar(paquete(), "tv", enfasis="dato")
        self.assertEqual(con["oraciones"][0]["evidencia_id"], "EV3")
        sin = adaptar(paquete(False), "tv", enfasis="dato")
        self.assertIn("No hay indicador oficial citado", " ".join(sin["avisos"]))
        self.assertEqual(sin["oraciones"][0]["evidencia_id"], "EV1")

    def test_alerta_no_supera_140_caracteres(self):
        result = adaptar(paquete(), "alerta")
        self.assertLessEqual(result["contador"]["caracteres"], 140)

    def test_guardian_retira_oracion_inventada_inyectada(self):
        p = paquete()
        p["afirmaciones"].append({"id": "AF-X", "texto": "El cierre afectó maíz y frutas tropicales.", "tipo": "inferencia", "evidencia_id": "EV1", "campo": "titulo"})
        result = adaptar(p, "tv")
        self.assertTrue(any("Terminos sin respaldo" in item["motivo"] for item in result["retiradas"]))
        self.assertNotIn("maíz", result["texto"])


class FormatosApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = temporary_directory()
        self.addCleanup(self.temp.cleanup)
        self.path = self.temp.name + "/formatos-api.sqlite"
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
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        self.addCleanup(conn.close)
        conn.request("POST", "/api/borradores/SYN-B1/adaptar",
                     body=json.dumps(body).encode("utf-8"),
                     headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        return response.status, json.loads(response.read().decode("utf-8"))

    def test_api_adaptar_200(self):
        status, payload = self.request({"formato": "web", "tono": "sobrio"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["formato"], "web")
        self.assertIn("payload_version", payload)

    def test_api_adaptar_400(self):
        status, payload = self.request({"formato": "urgente"})
        self.assertEqual(status, 400)
        self.assertIn("Formato inválido", payload["error"])


if __name__ == "__main__":
    unittest.main()


class FormatosCorreccionesTests(unittest.TestCase):
    """Defectos vistos con un borrador real el 2026-10-07: afirmación duplicada y «qué falta» retirado."""

    def _con_duplicado(self):
        p = paquete(con_indicador=False)
        primera = p["afirmaciones"][0]
        p["afirmaciones"].append({**primera, "id": "AF1-GUION", "texto": primera["texto"].rstrip(".") + ". (Titular · TVN)."})
        return p

    def test_afirmacion_repetida_en_brief_y_guion_sale_una_vez(self):
        r = adaptar(self._con_duplicado(), "tv")
        self.assertEqual(r["texto"].count("Canal de Panamá reduce calado"), 1)

    def test_que_falta_verificar_no_lo_retira_el_guardian_y_abre_con_enfasis(self):
        r = adaptar(self._con_duplicado(), "web", enfasis="verificacion")
        self.assertTrue(r["texto"].startswith("Qué falta verificar"))
        self.assertEqual(r["texto"].count("Falta verificar:"), 1)
        tv = adaptar(self._con_duplicado(), "tv", enfasis="verificacion")
        self.assertEqual(tv["texto"].count("Falta verificar:"), 1)

    def test_tono_explicativo_solo_usa_conteos_de_la_evidencia(self):
        r = adaptar(self._con_duplicado(), "web", tono="explicativo")
        self.assertIn("2 medios publicaron este tema (Agencia, TVN)", r["texto"])
