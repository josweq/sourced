import unittest

from scripts.check_contraste import main


class ContrastGateTests(unittest.TestCase):
    def test_visual_tokens_pass_contrast_gate(self):
        self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
