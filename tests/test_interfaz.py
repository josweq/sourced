import json
from pathlib import Path
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import tempfile
import threading
import unittest

from scripts.modelo_datos import DEFAULT_FIXTURE, load_fixture, save_new
from src.interfaz.app import Handler, add_review, case_detail, connect, list_cases
from tests.helpers import temporary_directory

ROOT = Path(__file__).resolve().parents[1]


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = temporary_directory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "ui.sqlite"
        db = load_fixture(json.loads(DEFAULT_FIXTURE.read_text(encoding="utf-8")))
        save_new(db, self.path)
        db.close()

    def test_agenda_and_detail(self):
        with connect(self.path) as db:
            self.assertEqual(len(list_cases(db)), 5)
            detail = case_detail(db, "SYN-C1")
            self.assertEqual(detail["caso"]["estado_revision"], "en_revision")
            self.assertEqual(detail["evidencias"][0]["valor"], 7.25)
            self.assertEqual(detail["borradores"][0]["afirmaciones"][0]["evidencia_id"], "SYN-E1")

    def test_review_is_persisted_and_sequenced(self):
        with connect(self.path) as db:
            result = add_review(db, "SYN-C1", {"persona_revisora": "Prueba local",
                "estado": "requiere_evidencia", "comentario": "Falta fuente actual.",
                "borrador_id": "SYN-B1"})
            self.assertEqual(result["secuencia"], 2)
        with connect(self.path) as db:
            self.assertEqual(case_detail(db, "SYN-C1")["caso"]["estado_revision"], "requiere_evidencia")

    def test_approval_requires_case_draft(self):
        with connect(self.path) as db:
            with self.assertRaises(ValueError):
                add_review(db, "SYN-C4", {"persona_revisora": "Prueba local",
                    "estado": "aprobado_como_borrador", "comentario": "Aprobar.",
                    "borrador_id": ""})


class StaticServerTests(unittest.TestCase):
    def setUp(self):
        Handler.db_path = ROOT / "tests" / "no-static-db-needed.sqlite"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.thread.join, 1)
        self.addCleanup(self.server.shutdown)

    def request(self, path):
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        self.addCleanup(conn.close)
        conn.request("GET", path)
        return conn.getresponse()

    def test_new_static_mime_types(self):
        expected = {
            "/tokens.css": "text/css; charset=utf-8",
            "/img/lupa.svg": "image/svg+xml",
            "/favicon.svg": "image/svg+xml",
            "/fonts/Inter-Regular.woff2": "font/woff2",
        }
        for path, content_type in expected.items():
            with self.subTest(path=path):
                response = self.request(path)
                self.assertEqual(response.status, 200)
                self.assertEqual(response.getheader("Content-Type"), content_type)

    def test_static_path_traversal_returns_404(self):
        response = self.request("/fonts/../app.py")
        self.assertEqual(response.status, 404)


if __name__ == "__main__":
    unittest.main()
