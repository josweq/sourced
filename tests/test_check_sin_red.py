"""La puerta estática de T10 pasa sobre el repo y falla cuando se le mete una salida a la red."""
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.check_sin_red import revisar

RAIZ = Path(__file__).resolve().parents[1]


class CheckSinRedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(RAIZ / "src", self.tmp / "src", ignore=shutil.ignore_patterns("__pycache__", "fonts", "img"))
        (self.tmp / "scripts").mkdir()
        shutil.copy(RAIZ / "scripts" / "smoke_sin_red.py", self.tmp / "scripts")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_repo_pasa(self):
        self.assertEqual(revisar(RAIZ), [])

    def test_cliente_de_red_fuera_de_lugar_falla(self):
        (self.tmp / "src" / "ia" / "fuga.py").write_text("import requests\n", encoding="utf-8")
        fallos = revisar(self.tmp)
        self.assertTrue(any("fuga.py" in f and "requests" in f for f in fallos), fallos)

    def test_url_externa_en_la_interfaz_falla(self):
        js = self.tmp / "src" / "interfaz" / "static" / "fuga.js"
        js.write_text('fetch("https://cdn.example.com/x.js")\n', encoding="utf-8")
        fallos = revisar(self.tmp)
        self.assertTrue(any("cdn.example.com" in f for f in fallos), fallos)

    def test_proveedor_por_defecto_remoto_falla(self):
        ruta = self.tmp / "src" / "ia" / "proveedores.py"
        ruta.write_text(ruta.read_text(encoding="utf-8").replace('"LUPA_PROVEEDOR", "ollama"', '"LUPA_PROVEEDOR", "openai_compat"'), encoding="utf-8")
        fallos = revisar(self.tmp)
        self.assertTrue(any("proveedor por defecto" in f for f in fallos), fallos)


if __name__ == "__main__":
    unittest.main()
