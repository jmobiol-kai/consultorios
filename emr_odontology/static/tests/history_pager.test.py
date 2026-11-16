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

    def test_procedure_summary_names_tooth_and_face(self):
        self.assertEqual(
            self.pager.procedure_summary([
                ("Caries", "Distal", "14"),
                ("Corona", "Pieza", "36"),
                ("", "Mesial", ""),
            ]),
            "Caries distal 14, Corona 36, mesial",
        )
        self.assertEqual(self.pager.procedure_summary([]), "")

    def test_opening_a_row_keeps_the_pager_order(self):
        page_ids = self.pager.pager_page_ids(5, [8, 7])
        client = self.pager.odontogram_pager_client_action(
            12, page_ids, "Odontograma", current_id=page_ids[1]
        )
        self.assertEqual(client["params"]["res_id"], page_ids[1])
        self.assertEqual(client["params"]["res_ids"], page_ids)
        self.assertEqual(client["params"]["res_ids"][0], self.pager.chart_page_id(5))

    def test_page_ids_are_even_for_the_chart_and_odd_for_visits(self):
        # Odontograma 5 y consulta 5 no pueden pisarse: 10 y 11.
        self.assertEqual(self.pager.chart_page_id(5), 10)
        self.assertEqual(self.pager.visit_page_id(5), 11)
        self.assertEqual(
            self.pager.pager_page_ids(5, [8, 7, 4]),
            [10, 17, 15, 9],
        )

    def test_the_view_uses_the_same_ids_and_skips_empty_drafts(self):
        sql = self.pager.PAGE_VIEW_SQL
        self.assertIn("o.id * 2", sql)
        self.assertIn("e.id * 2 + 1", sql)
        self.assertIn("enc.state = 'draft'", sql)
        self.assertIn("enc.order_id IS NULL", sql)
        self.assertIn("e.reason", sql)
        self.assertIn("e.notes", sql)
        self.assertIn("emr_encounter_odontology_line", sql)
        self.assertIn("emr_diagnosis_emr_encounter_rel", sql)

    def test_client_action_hands_the_ids_to_props_not_to_the_window(self):
        page_ids = self.pager.pager_page_ids(5, [8, 7])
        client = self.pager.odontogram_pager_client_action(12, page_ids, "Odontograma")
        self.assertEqual(client["type"], "ir.actions.client")
        self.assertEqual(client["tag"], "emr_odontogram_pager")
        self.assertEqual(client["params"]["res_ids"], page_ids)
        self.assertEqual(client["params"]["res_id"], page_ids[0])
        window = self.pager.window_action_from_pager_params(client["params"])
        self.assertTrue(self.action_window.action_is_valid_for_do_action(window))
        self.assertNotIn("res_ids", window)
        self.assertEqual(window["res_id"], page_ids[0])
        self.assertEqual(window["views"], [[12, "form"]])
        js = (
            _ROOT / "static" / "src" / "odontogram" / "odontogram_pager.js"
        ).read_text(encoding="utf-8")
        self.assertIn('add("emr_odontogram_pager"', js)
        self.assertIn("params.res_ids", js)
        self.assertIn("resIds", js)
        self.assertIn("doAction", js)

    def test_opening_does_not_write_page_rows(self):
        source = (_ROOT / "models" / "res_partner.py").read_text(encoding="utf-8")
        self.assertIn("action_open_for_partner", source)
        page = (_ROOT / "models" / "emr_odontogram_page.py").read_text(encoding="utf-8")
        self.assertIn("_auto = False", page)
        self.assertIn("def write", page)
        self.assertIn('odontogram_id.write({"tooth_ids"', page)
        self.assertIn("history_visit_ids", page)
        self.assertIn("is_empty_draft", page)
        self.assertIn("pager_page_ids", page)
        self.assertNotIn(".unlink(", page)
        self.assertNotIn("self.create(", page)
        self.assertIn("partner_id.action_odontology_walkin", page)
        migration = (
            _ROOT / "migrations" / "19.0.1.19.0" / "pre-migrate.py"
        ).read_text(encoding="utf-8")
        self.assertIn("DROP TABLE IF EXISTS emr_odontogram_page", migration)
        manifest = (_ROOT / "__manifest__.py").read_text(encoding="utf-8")
        self.assertIn('"version": "19.0.1.19.4"', manifest)
        self.assertIn("def pager_ids_for", page)
        self.assertIn("odontogram_page_form.js", manifest)
        self.assertIn("_compute_history_ids", page)
        self.assertIn("action_open_page", page)
        self.assertIn("current_id", page)
        self.assertIn("odontogram_pager.js", manifest)

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
        text = (_ROOT / "views" / "emr_odontogram_page_views.xml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(form.get("js_class"), "emr_odontogram_page")
        self.assertIsNone(form.find("header"))
        bar = next(
            node
            for node in form.iter("div")
            if "display:flex" in (node.get("style") or "")
        )
        self.assertIsNotNone(bar)
        self.assertIn("align-items:center", bar.get("style"))
        button = bar.find("button")
        self.assertEqual(button.get("string"), "Atender ahora")
        self.assertEqual(button.get("invisible"), "kind != 'chart'")
        headings = bar.findall("h1")
        self.assertEqual(len(headings), 2)
        self.assertEqual((headings[0].text or "").strip(), "Historia Clínica")
        self.assertEqual(headings[0].get("invisible"), "kind != 'chart'")
        self.assertIn("white-space:nowrap", headings[0].get("style"))
        self.assertIn("font-size:2rem", headings[0].get("style"))
        self.assertIn("flex:1", headings[0].get("style"))
        self.assertEqual(headings[1].get("invisible"), "kind != 'visit'")
        self.assertEqual((headings[1].find("span").text or "").strip(), "Consulta")
        form_js = (
            _ROOT / "static" / "src" / "odontogram" / "odontogram_page_form.js"
        ).read_text(encoding="utf-8")
        self.assertIn("pager_ids_for", form_js)
        self.assertIn("resIds", form_js)
        history = [
            field for field in root.iter("field") if field.get("name") == "history_ids"
        ]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].get("readonly"), "1")
        table = history[0].find("list")
        self.assertEqual(table.get("create"), "false")
        self.assertEqual(table.get("delete"), "false")
        self.assertEqual(
            [field.get("name") for field in table.findall("field")],
            [
                "visit_date",
                "practitioner_id",
                "procedure_summary",
                "amount_total",
                "currency_id",
                "order_id",
                "order_state",
            ],
        )
        opener = table.find("button")
        self.assertEqual(opener.get("name"), "action_open_page")
        self.assertEqual(opener.get("string"), "Abrir")
        chart = text.find('widget="odontogram_chart"')
        history_at = text.find('name="history_ids"')
        visit_chart = text.find('widget="odontogram_chart"', chart + 1)
        self.assertLess(chart, history_at)
        self.assertLess(history_at, visit_chart)


if __name__ == "__main__":
    unittest.main()
