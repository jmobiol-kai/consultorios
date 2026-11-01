"""La atención no pide paciente y profesional antes de mostrar la historia.

Sin Odoo: se lee el XML. Nuevo tiene que quedar a la izquierda de
Atendido, y el menú tiene que abrir la consulta, no un asistente.
"""
import pathlib
import unittest
import xml.etree.ElementTree as ET

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_VIEW = _ROOT / "views" / "emr_encounter_views.xml"
_BASE = _ROOT.parents[0] / "emr" / "views" / "emr_encounter_form_base.xml"
_WIZARD = _ROOT / "wizards" / "emr_odontology_walkin.py"


def _record(root, xmlid):
    for record in root.iter("record"):
        if record.get("id") == xmlid:
            return record
    raise AssertionError(xmlid)


class AttentionScreenTest(unittest.TestCase):
    def setUp(self):
        self.root = ET.parse(_VIEW).getroot()

    def test_nuevo_is_immediately_left_of_atendido(self):
        found = False
        for xpath in self.root.iter("xpath"):
            if xpath.get("expr") != "//header/button[@name='action_close']":
                continue
            self.assertEqual(xpath.get("position"), "before")
            button = xpath.find("button")
            self.assertIsNotNone(button)
            self.assertEqual(button.get("name"), "action_new_quotation")
            self.assertEqual(button.get("string"), "Nuevo")
            found = True
        self.assertTrue(found)

    def test_atendido_stays_on_the_base_form(self):
        base = ET.parse(_BASE).getroot()
        atendido = [
            button
            for button in base.iter("button")
            if button.get("name") == "action_close"
        ]
        self.assertEqual(len(atendido), 1)
        self.assertEqual(atendido[0].get("string"), "Atendido")

    def test_menu_opens_the_encounter_not_a_dialog(self):
        action = _record(self.root, "emr_odontology_walkin_action")
        fields = {
            field.get("name"): (field.text or "").strip()
            for field in action.findall("field")
        }
        self.assertEqual(fields["res_model"], "emr.encounter.odontology")
        self.assertEqual(fields["view_mode"], "form")
        self.assertEqual(fields["target"], "current")
        self.assertNotIn("emr.odontology.walkin", ET.tostring(self.root, encoding="unicode"))

    def test_patient_is_chosen_on_the_screen_until_there_is_a_quote(self):
        readonly = [
            field.get("readonly")
            for field in self.root.iter("field")
            if field.get("name") == "partner_id" and field.get("readonly")
        ]
        self.assertIn("order_id or state != 'draft'", readonly)

    def test_walkin_wizard_is_gone(self):
        self.assertFalse(_WIZARD.exists())


if __name__ == "__main__":
    unittest.main()
