"""El cierre no puede quedar con prácticas y sin presupuesto.

Sin Odoo: la decisión de crear el pedido y de tirar un borrador vacío
está en funciones puras. Se cargan por archivo para no ejecutar
models/__init__.py, que importa Odoo.
"""
import importlib.util
import pathlib
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load(name, relative):
    path = _ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_billing = _load("billing_rules", "models/billing_rules.py")
_profile = _load("dental_profile", "models/dental_profile.py")
needs_quotation = _billing.needs_quotation
is_empty_draft = _billing.is_empty_draft
cleanup_partner_ids = _billing.cleanup_partner_ids
DENTAL_HIDDEN_MENU_XMLIDS = _profile.DENTAL_HIDDEN_MENU_XMLIDS
dental_profile_enabled = _profile.dental_profile_enabled


class BillingRulesTest(unittest.TestCase):
    def test_billable_marks_without_an_order_need_a_quotation(self):
        marks = [("pending", "caries"), ("treated", "crown")]
        self.assertTrue(
            needs_quotation(False, marks, ("pending", "treated"), {"caries", "crown"})
        )

    def test_an_existing_order_is_not_created_again(self):
        marks = [("pending", "extraction")]
        self.assertFalse(
            needs_quotation(True, marks, ("pending", "treated"), {"extraction"})
        )

    def test_sound_and_notes_do_not_invent_a_quotation(self):
        marks = [("present", "sound"), ("missing", "missing")]
        self.assertFalse(
            needs_quotation(False, marks, ("pending", "treated"), {"caries", "crown"})
        )
        self.assertFalse(
            needs_quotation(False, [], ("pending", "treated"), {"caries"})
        )

    def test_cleanup_stays_on_the_same_patient(self):
        self.assertEqual(cleanup_partner_ids([5, False, 5, None]), [5])
        self.assertEqual(cleanup_partner_ids([False]), [])
        self.assertEqual(cleanup_partner_ids([]), [])
        self.assertEqual(cleanup_partner_ids([8, 9]), [8, 9])

    def test_empty_draft_has_nothing_clinical(self):
        self.assertTrue(is_empty_draft("draft", False, 0, "", "", 0))
        self.assertTrue(is_empty_draft("draft", False, 0, "   ", None, 0))
        self.assertFalse(is_empty_draft("draft", False, 1, "", "", 0))
        self.assertFalse(is_empty_draft("draft", True, 0, "", "", 0))
        self.assertFalse(is_empty_draft("draft", False, 0, "dolor", "", 0))
        self.assertFalse(is_empty_draft("closed", False, 0, "", "", 0))
        self.assertFalse(is_empty_draft("draft", False, 0, "", "", 1))

    def test_dental_profile_hides_only_the_daily_unused_emr_menus(self):
        self.assertEqual(
            DENTAL_HIDDEN_MENU_XMLIDS,
            (
                "emr.menu_emr_medications",
                "emr.menu_emr_allergies",
                "emr.menu_emr_settlement",
            ),
        )
        self.assertTrue(dental_profile_enabled("True"))
        self.assertTrue(dental_profile_enabled(" true "))
        self.assertFalse(dental_profile_enabled("False"))
        self.assertFalse(dental_profile_enabled(""))
        self.assertFalse(dental_profile_enabled(None))


if __name__ == "__main__":
    unittest.main()
