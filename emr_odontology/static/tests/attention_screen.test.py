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

    def test_past_visit_locks_the_clinical_fields(self):
        locked = {}
        for field in self.root.iter("field"):
            name = field.get("name")
            if name in {"reason", "notes", "diagnosis_ids", "line_ids"} and field.get("readonly"):
                locked.setdefault(name, []).append(field.get("readonly"))
        self.assertEqual(
            locked,
            {
                "reason": ["state != 'draft'"],
                "notes": ["state != 'draft'"],
                "line_ids": ["state != 'draft'", "state != 'draft'"],
                "diagnosis_ids": ["state != 'draft'"],
            },
        )

    def test_history_card_hides_nuevo_and_the_quote(self):
        invisible = {
            button.get("name"): button.get("invisible")
            for button in self.root.iter("button")
            if button.get("name") in {"action_new_quotation", "action_view_sale_order"}
        }
        self.assertEqual(
            invisible["action_new_quotation"],
            "context.get('emr_history_readonly') or state != 'draft'",
        )
        self.assertIn("state != 'draft'", invisible["action_new_quotation"])
        self.assertIn("emr_history_readonly", invisible["action_view_sale_order"])

    def test_odontogram_faces_do_not_select_when_readonly(self):
        source = (
            _ROOT / "static" / "src" / "odontogram" / "odontogram_chart.js"
        ).read_text(encoding="utf-8")
        region = source.split("async onRegion", 1)[1].split("async onTooth", 1)[0]
        tooth = source.split("async onTooth", 1)[1].split("async clearSelectionMark", 1)[0]
        legend = source.split("async onLegend", 1)[1].split("async applyCondition", 1)[0]
        for handler in (region, tooth, legend):
            self.assertLess(
                handler.index("chartEditsAllowed"),
                handler.index("return;"),
            )
        chart = (
            _ROOT / "static" / "src" / "odontogram" / "odontogram_chart.xml"
        ).read_text(encoding="utf-8")
        self.assertIn("Consulta registrada", chart)

    def test_patient_is_chosen_on_the_screen_until_there_is_a_quote(self):
        readonly = [
            field.get("readonly")
            for field in self.root.iter("field")
            if field.get("name") == "partner_id" and field.get("readonly")
        ]
        self.assertIn("order_id or state != 'draft'", readonly)

    def test_walkin_wizard_is_gone(self):
        self.assertFalse(_WIZARD.exists())

    def test_generic_create_is_off_on_the_form(self):
        found = False
        for xpath in self.root.iter("xpath"):
            if xpath.get("expr") != "//form" or xpath.get("position") != "attributes":
                continue
            for attribute in xpath.findall("attribute"):
                if attribute.get("name") != "create":
                    continue
                self.assertEqual((attribute.text or "").strip(), "false")
                found = True
        self.assertTrue(found)

    def test_header_nuevo_is_not_the_generic_create(self):
        for button in self.root.iter("button"):
            if button.get("string") != "Nuevo":
                continue
            self.assertEqual(button.get("name"), "action_new_quotation")
            self.assertEqual(button.get("type"), "object")
            self.assertNotEqual(button.get("name"), "create")


if __name__ == "__main__":
    unittest.main()
