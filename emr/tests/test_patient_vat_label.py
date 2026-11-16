"""El rótulo del país no pisa el DNI del paciente."""
from lxml import etree

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPatientVatLabel(TransactionCase):
    def test_patient_vat_stays_dni_when_the_country_says_cuit(self):
        country = self.env.ref("base.ar")
        country.vat_label = "CUIT"
        self.env.company.country_id = country
        self.env.registry.clear_cache("templates")

        views = self.env["res.partner"].get_views([(False, "form")])
        root = etree.fromstring(views["views"]["form"]["arch"].encode())
        patient = [
            node for node in root.xpath("//field[@name='vat']")
            if "o_emr_patient_dni" in (node.get("class") or "").split()
        ]
        self.assertEqual(len(patient), 1)
        self.assertEqual(patient[0].get("string"), "DNI")
        self.assertEqual(patient[0].get("invisible"), "not is_patient")

        others = [
            node for node in root.xpath("//field[@name='vat']|//label[@for='vat']")
            if node not in patient
        ]
        self.assertTrue(any(node.get("string") == "CUIT" for node in others))
        for node in others:
            self.assertNotEqual(node.get("string"), "DNI")
