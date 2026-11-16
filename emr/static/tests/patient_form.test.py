"""La ficha del paciente es de una persona con DNI.

Sin Odoo: se leen las reglas y el XML. Una obra social no entra en
esas reglas.
"""
import importlib.util
import pathlib
import unittest
import xml.etree.ElementTree as ET

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PATH = _ROOT / "models" / "patient_form.py"
_VIEW = _ROOT / "views" / "res_partner_views.xml"


def _load():
    spec = importlib.util.spec_from_file_location("patient_form", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PatientFormTest(unittest.TestCase):
    def setUp(self):
        self.mod = _load()
        self.root = ET.parse(_VIEW).getroot()

    def test_patient_is_a_person_and_gets_dni_when_the_type_exists(self):
        self.assertEqual(self.mod.DNI_XMLID, "l10n_ar.it_dni")
        self.assertEqual(
            self.mod.patient_identity_defaults(True, 7, True),
            {
                "is_company": False,
                "company_type": "person",
                "l10n_latam_identification_type_id": 7,
            },
        )

    def test_without_argentine_localization_the_type_is_not_set(self):
        self.assertEqual(
            self.mod.patient_identity_defaults(True, False, False),
            {"is_company": False, "company_type": "person"},
        )
        self.assertEqual(
            self.mod.patient_identity_defaults(True, False, True),
            {"is_company": False, "company_type": "person"},
        )

    def test_other_contacts_are_left_alone(self):
        self.assertEqual(self.mod.patient_identity_defaults(False, 7, True), {})

    def test_existing_patients_with_another_document_type_switch_to_dni(self):
        dni = 5
        self.assertEqual(
            self.mod.patient_ids_to_switch_to_dni([(1, 8), (2, 5), (3, False), (4, 9)], dni),
            [1, 3, 4],
        )
        self.assertEqual(self.mod.patient_ids_to_switch_to_dni([(1, 8)], False), [])

    def test_dni_label_is_not_treated_as_the_generic_one(self):
        self.assertTrue(self.mod.is_patient_document_label("DNI"))
        self.assertFalse(self.mod.is_patient_document_label("Tax ID"))
        self.assertFalse(self.mod.is_patient_document_label("CUIT"))

    def test_identification_type_stays_hidden_only_for_patients(self):
        self.assertEqual(self.mod.merge_invisible(""), "is_patient")
        self.assertEqual(
            self.mod.merge_invisible("is_vat and 'LATAMID' not in fiscal_country_group_codes"),
            "(is_vat and 'LATAMID' not in fiscal_country_group_codes) or is_patient",
        )

    def test_patient_fields_move_out_of_the_notebook(self):
        pages = [
            page.get("name")
            for page in self.root.iter("page")
        ]
        self.assertNotIn("emr_patient", pages)
        self.assertIn("emr_practitioner", pages)
        self.assertIn("emr_insurer", pages)
        group = next(
            node for node in self.root.iter("group") if node.get("name") == "emr_patient"
        )
        self.assertEqual(group.get("invisible"), "not is_patient")
        names = {field.get("name") for field in group.iter("field")}
        self.assertEqual(
            names,
            {"birthdate_date", "gender", "insurer_id", "insurance_member_number"},
        )
        notebook = self.root.find(".//xpath[@expr='//notebook'][@position='before']")
        self.assertIsNotNone(notebook)

    def test_standard_contact_fields_hide_only_for_patients(self):
        attrs = {}
        for xpath in self.root.iter("xpath"):
            field = xpath.get("expr")
            attribute = xpath.find("attribute")
            if attribute is not None and attribute.get("name") == "invisible":
                attrs[field] = (attribute.text or "").strip()
        self.assertEqual(attrs["//field[@name='company_type']"], "is_patient")
        self.assertEqual(
            attrs["//group/field[@name='function']"],
            "is_company or is_patient",
        )
        self.assertNotIn("placeholder", " ".join(attrs))
        self.assertEqual(attrs["//field[@name='website']"], "is_patient")
        dni_labels = [
            node for node in self.root.iter("label")
            if node.get("for") == "vat" and node.get("string") == "DNI"
        ]
        self.assertEqual(len(dni_labels), 1)
        self.assertEqual(dni_labels[0].get("invisible"), "not is_patient")
        self.assertIn("is_patient", attrs["//field[@name='parent_id']"])
        self.assertIn("is_patient", attrs["//field[@name='company_name']/parent::div"])
        source = (_ROOT / "models" / "res_partner.py").read_text(encoding="utf-8")
        self.assertIn('env.ref(DNI_XMLID, raise_if_not_found=False)', source)


if __name__ == "__main__":
    unittest.main()
