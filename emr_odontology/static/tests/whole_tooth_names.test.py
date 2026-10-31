"""Grafías que prenden Pieza entera en filas ya cargadas.

No importa el paquete del módulo: ese __init__ pide Odoo. Carga el
helper por archivo.
"""
import importlib.util
import pathlib
import unittest

_PATH = pathlib.Path(__file__).resolve().parents[2] / "models" / "whole_tooth.py"
_SPEC = importlib.util.spec_from_file_location("whole_tooth", _PATH)
whole_tooth = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(whole_tooth)


class WholeToothNamesTest(unittest.TestCase):
    def test_factory_codes_match_even_if_renamed(self):
        self.assertTrue(whole_tooth.matches_whole_tooth("crown", "Fundita"))
        self.assertTrue(whole_tooth.matches_whole_tooth("implant", "Implante"))
        self.assertTrue(whole_tooth.matches_whole_tooth("extraction", "Otra"))
        self.assertTrue(whole_tooth.matches_whole_tooth("missing", "Ausente"))
        self.assertTrue(whole_tooth.matches_whole_tooth("prosthesis", "Puente"))
        self.assertTrue(whole_tooth.matches_whole_tooth("sound", "Saludable"))

    def test_spanish_spellings_without_the_factory_code(self):
        names = [
            "Implante",
            "implante",
            "IMPLANTE",
            "Prótesis",
            "Protesis",
            "protesis",
            "  Prótesis  ",
            "Ausente",
            "Sano",
            "Corona",
            "Extracción indicada",
            "Extraccion indicada",
            "EXTRACCIÓN INDICADA",
            "Extracción",
            "Extraccion",
            "Prótesis fija",
            "Implante dental",
            "Extracción indicada (urgencia)",
        ]
        for name in names:
            self.assertTrue(
                whole_tooth.matches_whole_tooth("hecho_a_mano", name),
                name,
            )

    def test_face_conditions_stay_face_level(self):
        for name in [
            "Caries",
            "Obturación",
            "Obturacion",
            "Endodoncia",
            "Fractura",
            "Sellador",
            "",
            "Fundita",
        ]:
            self.assertFalse(
                whole_tooth.matches_whole_tooth("hecho_a_mano", name),
                name,
            )
        self.assertFalse(whole_tooth.matches_whole_tooth("caries", "Caries"))
        self.assertFalse(whole_tooth.matches_whole_tooth("restoration", "Obturación"))
        self.assertFalse(whole_tooth.matches_whole_tooth("endodontics", "Endodoncia"))
        self.assertFalse(whole_tooth.matches_whole_tooth("fracture", "Fractura"))
        self.assertFalse(whole_tooth.matches_whole_tooth("sealant", "Sellador"))


if __name__ == "__main__":
    unittest.main()
