from pathlib import Path
import shutil
import unittest

from scripts.extraccion import rss_medios
from tests.helpers import temporary_directory

MUESTRA = Path(__file__).resolve().parent / "fixtures" / "extraccion" / "tvn_rss_muestra.xml"


class RssMediosTests(unittest.TestCase):
    def test_lee_varios_medios_y_deduplica_entre_ellos(self):
        with temporary_directory() as tmp:
            for clave in ("tvn", "prensa"):
                (Path(tmp) / clave).mkdir()
                shutil.copyfile(MUESTRA, Path(tmp) / clave / f"{clave}_1.xml")
            excluidos = []
            filas, _ = rss_medios.filas_desde_capturas(tmp, "2026-10-08T00:00:00Z", excluidos)
            self.assertEqual(len(filas), 3)
            self.assertEqual({f["medio"] for f in filas}, {"TVN"})
            self.assertTrue(all(f["alcance_texto"] == "titular_metadatos" for f in filas))
            self.assertEqual(sum(e["causa"] == "duplicado_url_normalizada" for e in excluidos), 3)
            for fila in filas:
                self.assertNotIn("description", fila)

    def test_un_medio_caido_no_detiene_a_los_demas(self):
        def obtener(url, pausa_min_s=0):
            if "critica" in url:
                raise RuntimeError("HTTP 500")
            return MUESTRA.read_bytes()

        with temporary_directory() as tmp:
            guardadas, fallidas = rss_medios.capturar_todos(tmp, obtener, "2026-10-08T00:00:00Z")
            self.assertEqual(len(guardadas), len(rss_medios.MEDIOS) - 1)
            self.assertEqual([f["medio"] for f in fallidas], ["critica"])

    def test_respuesta_no_xml_se_registra_como_fallida(self):
        with temporary_directory() as tmp:
            _, fallidas = rss_medios.capturar_todos(tmp, lambda url, pausa_min_s=0: b"<html>no", "2026-10-08T00:00:00Z")
            self.assertEqual(len(fallidas), len(rss_medios.MEDIOS))

    def test_fuentes_un_registro_por_medio(self):
        ids = {f["id"] for f in rss_medios.fuentes("2026-10-08T00:00:00Z")}
        self.assertEqual(len(ids), len(rss_medios.MEDIOS))


if __name__ == "__main__":
    unittest.main()
