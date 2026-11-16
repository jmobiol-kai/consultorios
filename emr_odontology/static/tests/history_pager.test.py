"""El paginador del odontograma: primero el mapa, después las consultas.

Sin Odoo: el orden y la acción se leen directo. La vista se parsea.
"""
import importlib.util
import pathlib
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PAGER = _ROOT / "models" / "history_pager.py"
_ACTION = _ROOT.parents[0] / "emr" / "models" / "action_window.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HistoryPagerTest(unittest.TestCase):
    def setUp(self):
        self.pager = _load("history_pager", _PAGER)
        self.action_window = _load("action_window", _ACTION)

    def test_newest_consultation_comes_first_and_empty_drafts_stay_out(self):
        january = datetime(2026, 1, 15, 10, 0)
        june = datetime(2026, 6, 2, 9, 30)
        june_later = datetime(2026, 6, 2, 18, 0)
        visits = self.pager.history_visit_ids([
            (4, january, False),
            (9, june, True),
            (7, june_later, False),
            (8, june_later, False),
            (0, june, False),
        ])
        self.assertEqual(visits, [8, 7, 4])

    def test_no_consultations_is_an_empty_list(self):
        self.assertEqual(self.pager.history_visit_ids([]), [])
        self.assertEqual(
            self.pager.history_visit_ids([(3, datetime(2026, 1, 1), True)]),
            [],
        )

    def test_pager_opens_the_chart_and_then_each_consultation(self):
        action = self.pager.odontogram_pager_action(12, [100, 30, 10], "Odontograma")
        self.assertTrue(self.action_window.action_is_valid_for_do_action(action))
        self.assertEqual(action["res_model"], "emr.odontogram.page")
        self.assertEqual(action["res_id"], 100)
        self.assertEqual(action["res_ids"], [100, 30, 10])
        self.assertEqual(action["views"], [[12, "form"]])
        self.assertEqual(action["context"], {"create": False})

    def test_the_patient_screen_uses_that_pager(self):
        source = (_ROOT / "models" / "res_partner.py").read_text(encoding="utf-8")
        self.assertIn("action_open_for_partner", source)
        page = (_ROOT / "models" / "emr_odontogram_page.py").read_text(encoding="utf-8")
        self.assertIn("history_visit_ids", page)
        self.assertIn("is_empty_draft", page)
        self.assertIn("action_odontology_walkin", page)
        self.assertIn("partner_id.action_odontology_walkin", page)
        manifest = (_ROOT / "__manifest__.py").read_text(encoding="utf-8")
        self.assertIn('"version": "19.0.1.18.0"', manifest)

    def test_visit_page_shows_the_order_the_price_and_a_readonly_chart(self):
        root = ET.parse(_ROOT / "views" / "emr_odontogram_page_views.xml").getroot()
        form = root.find(".//form")
        self.assertEqual(form.get("create"), "false")
        self.assertEqual(form.get("delete"), "false")
        attend = [
            button
            for button in root.iter("button")
            if button.get("name") == "action_odontology_walkin"
        ]
        self.assertEqual(len(attend), 1)
        self.assertEqual(attend[0].get("string"), "Atender ahora")
        self.assertEqual(attend[0].get("invisible"), "kind != 'chart'")
        names = {field.get("name") for field in root.iter("field")}
        self.assertTrue({
            "visit_date",
            "practitioner_id",
            "order_id",
            "order_state",
            "amount_total",
            "price_subtotal",
            "line_ids",
            "tooth_ids",
        }.issubset(names))
        charts = [
            field
            for field in root.iter("field")
            if field.get("widget") == "odontogram_chart"
        ]
        self.assertEqual(len(charts), 2)
        readonly_charts = [field for field in charts if field.get("readonly") == "1"]
        self.assertEqual(len(readonly_charts), 1)
        chart_form = ET.parse(_ROOT / "views" / "emr_odontogram_views.xml").getroot()
        still = [
            button
            for button in chart_form.iter("button")
            if button.get("name") == "action_odontology_walkin"
        ]
        self.assertEqual(len(still), 1)


if __name__ == "__main__":
    unittest.main()
