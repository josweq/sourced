import unittest

from src.ia.consulta import _bm25


class Bm25Test(unittest.TestCase):
    def test_termino_raro_pesa_mas_que_uno_comun(self):
        docs = [["canal", "cruceros"], ["canal", "lluvias"], ["canal", "transito"], ["cruceros", "turismo"]]
        p = _bm25(docs, ["canal", "cruceros"])
        self.assertEqual(int(p.argmax()), 0)
        self.assertAlmostEqual(float(p.max()), 1.0)
        self.assertGreater(p[3], p[1])

    def test_sin_coincidencias_da_ceros(self):
        p = _bm25([["canal"], ["lluvias"]], ["oro", "bolivia"])
        self.assertEqual(p.tolist(), [0.0, 0.0])

    def test_consulta_vacia(self):
        self.assertEqual(_bm25([["canal"]], []).tolist(), [0.0])


if __name__ == "__main__":
    unittest.main()
