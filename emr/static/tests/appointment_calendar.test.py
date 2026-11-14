"""Consultorio abre el calendario de turnos, sin el filtro Hoy.

Sin Odoo: se leen las vistas. La semana es la escala inicial, día y mes
siguen disponibles, y la grilla de huecos deja de arrancar en hoy.
"""
import pathlib
import unittest
import xml.etree.ElementTree as ET

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_ORDERS = _ROOT / "views" / "sale_order_views.xml"
_SLOTS = _ROOT / "views" / "emr_slot_views.xml"
_MENUS = _ROOT / "views" / "emr_menus.xml"


def _record(root, xmlid):
    for record in root.iter("record"):
        if record.get("id") == xmlid:
            return record
    raise AssertionError(xmlid)


def _fields(record):
    return {
        field.get("name"): (field.text or "").strip()
        for field in record.findall("field")
    }


class AppointmentCalendarTest(unittest.TestCase):
    def setUp(self):
        self.orders = ET.parse(_ORDERS).getroot()
        self.slots = ET.parse(_SLOTS).getroot()
        self.menus = ET.parse(_MENUS).getroot()

    def test_the_app_opens_the_appointment_calendar(self):
        root = next(
            item for item in self.menus.iter("menuitem") if item.get("id") == "menu_emr_root"
        )
        self.assertEqual(root.get("action"), "sale_order_action_appointment")
        action = _fields(_record(self.orders, "sale_order_action_appointment"))
        self.assertTrue(action["view_mode"].startswith("calendar"))
        self.assertNotIn("search_default_today", action["context"])
        self.assertIn("list", action["view_mode"])
        self.assertIn("kanban", action["view_mode"])

    def test_week_is_the_default_scale_and_professionals_are_filters(self):
        view = _record(self.orders, "sale_order_view_calendar_appointment")
        calendar = view.find(".//calendar")
        self.assertEqual(calendar.get("mode"), "week")
        self.assertEqual(calendar.get("scales"), "day,week,month")
        self.assertEqual(calendar.get("date_start"), "appointment_start")
        self.assertEqual(calendar.get("date_stop"), "appointment_stop")
        self.assertEqual(calendar.get("color"), "practitioner_id")
        self.assertEqual(calendar.get("js_class"), "emr_appointment_calendar")
        practitioner = next(
            field for field in calendar.findall("field") if field.get("name") == "practitioner_id"
        )
        self.assertEqual(practitioner.get("filters"), "1")
        self.assertEqual(practitioner.get("color"), "emr_calendar_color")

    def test_the_slot_board_does_not_open_on_today(self):
        action = _fields(_record(self.slots, "emr_slot_action"))
        self.assertNotIn("search_default_today", action.get("context", ""))


if __name__ == "__main__":
    unittest.main()
