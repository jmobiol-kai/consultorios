"""doAction de Odoo 19 exige views en un act_window.

Sin Odoo: se carga el armado de la acción y se rechaza el dict que
hacía fallar el popover (views ausente, .map sobre undefined).
"""
import importlib.util
import pathlib
import unittest

_PATH = pathlib.Path(__file__).resolve().parents[2] / "models" / "action_window.py"


def _load():
    spec = importlib.util.spec_from_file_location("action_window", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ActionWindowTest(unittest.TestCase):
    def setUp(self):
        self.mod = _load()

    def test_form_action_has_a_views_list(self):
        action = self.mod.act_window_form(
            "emr.encounter.odontology", 17, view_id=4, name="Atención"
        )
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "emr.encounter.odontology")
        self.assertEqual(action["res_id"], 17)
        self.assertEqual(action["views"], [[4, "form"]])
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual(action["target"], "current")
        self.assertTrue(self.mod.action_is_valid_for_do_action(action))

    def test_missing_views_is_what_broke_the_popover(self):
        broken = {
            "type": "ir.actions.act_window",
            "res_model": "emr.encounter.consultation",
            "res_id": 1,
            "view_mode": "form",
            "target": "current",
        }
        self.assertFalse(self.mod.action_is_valid_for_do_action(broken))
        self.assertIsNone(broken.get("views"))

    def test_a_view_pair_must_name_its_type(self):
        action = self.mod.act_window_form("sale.order", 3)
        self.assertEqual(action["views"], [[False, "form"]])
        self.assertTrue(self.mod.action_is_valid_for_do_action(action))
        action["views"] = [[1]]
        self.assertFalse(self.mod.action_is_valid_for_do_action(action))


if __name__ == "__main__":
    unittest.main()
