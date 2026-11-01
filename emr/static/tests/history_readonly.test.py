"""La tarjeta de la historia abre la atención en solo lectura.

Sin Odoo: se leen el JS y el XML. Odoo 19 ignora form_view_initial_mode
y un diálogo (target new) fuerza el formulario en edición, con Guardar
y Descartar. La tarjeta tiene que usar el diálogo de solo lectura.
"""
import pathlib
import unittest
import xml.etree.ElementTree as ET

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_JS = _ROOT / "static" / "src" / "patient_history" / "patient_history.js"
_BASE = _ROOT / "views" / "emr_encounter_form_base.xml"
_MANIFEST = _ROOT / "__manifest__.py"
_PRESCRIPTION = _ROOT.parent / "emr_prescription" / "views" / "emr_prescription_views.xml"


def _buttons(root):
    return list(root.iter("button"))


class HistoryReadonlyTest(unittest.TestCase):
    def test_history_card_opens_a_readonly_dialog(self):
        source = _JS.read_text(encoding="utf-8")
        self.assertIn("FormViewDialog", source)
        self.assertIn("readonly: true", source)
        self.assertIn("preventCreate: true", source)
        self.assertIn("preventEdit: true", source)
        self.assertIn("canExpand: false", source)
        self.assertIn("emr_history_readonly: true", source)
        self.assertNotIn("form_view_initial_mode:", source)
        self.assertNotIn("'form_view_initial_mode'", source)
        self.assertNotIn('target: "new"', source)

    def test_past_visit_switches_the_form_to_readonly(self):
        root = ET.parse(_BASE).getroot()
        widgets = [
            node.get("name")
            for node in root.iter("widget")
            if node.get("name") == "emr_encounter_readonly"
        ]
        self.assertEqual(widgets, ["emr_encounter_readonly"])
        manifest = _MANIFEST.read_text(encoding="utf-8")
        self.assertIn("encounter_readonly/*.js", manifest)

    def test_history_card_hides_write_buttons(self):
        root = ET.parse(_BASE).getroot()
        expected = {
            "action_close": "context.get('emr_history_readonly') or state != 'draft'",
            "action_wait": "context.get('emr_history_readonly') or state != 'draft'",
            "action_no_show": "context.get('emr_history_readonly') or state != 'draft'",
            "action_retype": "context.get('emr_history_readonly') or state != 'draft'",
            "action_sign": "context.get('emr_history_readonly') or state != 'closed'",
        }
        found = {}
        for button in _buttons(root):
            name = button.get("name")
            if name in expected:
                found[name] = button.get("invisible")
        self.assertEqual(found, expected)

    def test_attachments_lock_when_the_visit_is_not_draft(self):
        root = ET.parse(_BASE).getroot()
        readonly = [
            field.get("readonly")
            for field in root.iter("field")
            if field.get("name") == "attachment_ids"
        ]
        self.assertEqual(readonly, ["state != 'draft'"])

    def test_prescription_actions_stay_off_the_history_card(self):
        # La receta no hereda el formulario de la atención, así que sus
        # botones hay que apagarlos aparte. Autorizar o entregar desde
        # la tarjeta sería escribir una historia que se abrió para mirar.
        root = ET.parse(_PRESCRIPTION).getroot()
        found = {
            button.get("name"): button.get("invisible")
            for button in root.iter("button")
            if button.get("name") in {"action_authorize", "action_deliver"}
        }
        self.assertIn("emr_history_readonly", found["action_authorize"])
        self.assertIn("emr_history_readonly", found["action_deliver"])


if __name__ == "__main__":
    unittest.main()
