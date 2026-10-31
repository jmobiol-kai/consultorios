"""Profesional inicial de Atender ahora, sin Odoo.

El asistente importa odoo. Esta regla no: se carga el archivo suelto.
"""
import importlib.util
import pathlib
import unittest

_PATH = pathlib.Path(__file__).resolve().parents[2] / "wizards" / "walkin_default.py"
_SPEC = importlib.util.spec_from_file_location("walkin_default", _PATH)
walkin_default = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(walkin_default)


class WalkinDefaultTest(unittest.TestCase):
    def test_one_professional_is_selected_on_first_use(self):
        chosen = walkin_default.choose_walkin_practitioner(1, sole_id=7)
        self.assertEqual(chosen, 7)

    def test_one_professional_wins_over_a_stale_memory(self):
        chosen = walkin_default.choose_walkin_practitioner(
            1,
            sole_id=7,
            remembered_id=9,
            remembered_allowed=False,
        )
        self.assertEqual(chosen, 7)

    def test_several_professionals_use_the_remembered_one(self):
        chosen = walkin_default.choose_walkin_practitioner(
            3,
            remembered_id=2,
            remembered_allowed=True,
        )
        self.assertEqual(chosen, 2)

    def test_several_professionals_start_empty(self):
        self.assertFalse(walkin_default.choose_walkin_practitioner(4))
        self.assertFalse(
            walkin_default.choose_walkin_practitioner(
                4, remembered_id=False, remembered_allowed=False
            )
        )

    def test_remembered_professional_no_longer_allowed_stays_empty(self):
        chosen = walkin_default.choose_walkin_practitioner(
            2,
            remembered_id=9,
            remembered_allowed=False,
        )
        self.assertFalse(chosen)

    def test_nobody_available_stays_empty(self):
        self.assertFalse(walkin_default.choose_walkin_practitioner(0, sole_id=7))

    def test_each_user_has_their_own_key(self):
        key = walkin_default.walkin_practitioner_param_key
        self.assertNotEqual(key(3), key(8))
        self.assertTrue(key(3).endswith(".3"))
        self.assertTrue(key(8).endswith(".8"))

    def test_stored_value_parses_only_an_id(self):
        parse = walkin_default.parse_stored_practitioner_id
        self.assertEqual(parse("15"), 15)
        self.assertEqual(parse(" 15 "), 15)
        self.assertFalse(parse(False))
        self.assertFalse(parse(None))
        self.assertFalse(parse(""))
        self.assertFalse(parse("abc"))
        self.assertFalse(parse("0"))
        self.assertFalse(parse("15.0"))


if __name__ == "__main__":
    unittest.main()
