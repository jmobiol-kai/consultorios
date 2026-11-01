"""Título del panel de la consulta, sin Odoo.

El modelo importa odoo. Esta regla no: se carga el archivo suelto.
"""
import importlib.util
import pathlib
import unittest

_PATH = pathlib.Path(__file__).resolve().parents[2] / "models" / "encounter_title.py"
_SPEC = importlib.util.spec_from_file_location("encounter_title", _PATH)
encounter_title = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(encounter_title)


class EncounterTitleTest(unittest.TestCase):
    def test_empty_consultation_is_not_the_technical_name(self):
        title = encounter_title.encounter_control_panel_title(False)
        self.assertEqual(title, "Nueva consulta")
        self.assertNotIn("emr.encounter", title)
        self.assertNotIn(",", title)

    def test_missing_and_blank_names_use_the_same_fallback(self):
        title = encounter_title.encounter_control_panel_title
        self.assertEqual(title(None), title(""))
        self.assertEqual(title("   "), title(False))

    def test_patient_name_is_the_title(self):
        self.assertEqual(
            encounter_title.encounter_control_panel_title("  García, Ana  "),
            "García, Ana",
        )

    def test_fallback_can_be_translated_by_the_caller(self):
        self.assertEqual(
            encounter_title.encounter_control_panel_title(False, fallback="New visit"),
            "New visit",
        )

    def test_the_encounter_model_uses_this_title(self):
        source = (_PATH.parent / "emr_encounter.py").read_text(encoding="utf-8")
        self.assertIn(
            'display_name = fields.Char(compute="_compute_display_name")',
            source,
        )
        self.assertIn("encounter_control_panel_title(", source)
        self.assertIn("FALLBACK_TITLE", source)


if __name__ == "__main__":
    unittest.main()
