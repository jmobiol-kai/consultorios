"""El calendario muestra el paciente junto a la hora.

Sin Odoo: el nombre va en la primera línea y el tipo de visita, si hay,
en la segunda. No se repite el paciente como tipo.
"""
import importlib.util
import pathlib
import unittest

_PATH = pathlib.Path(__file__).resolve().parents[2] / "models" / "calendar_label.py"


def _load():
    spec = importlib.util.spec_from_file_location("calendar_label", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CalendarLabelTest(unittest.TestCase):
    def setUp(self):
        self.lines = _load().appointment_calendar_lines

    def test_patient_name_is_the_event_title(self):
        title, subtitle = self.lines("Juan Pérez", "Consulta odontológica")
        self.assertEqual(title, "Juan Pérez")
        self.assertEqual(subtitle, "Consulta odontológica")

    def test_missing_patient_stays_empty(self):
        self.assertEqual(self.lines("  ", "Consulta"), ("", "Consulta"))
        self.assertEqual(self.lines(None, None), ("", ""))

    def test_procedure_is_dropped_when_it_repeats_the_patient(self):
        self.assertEqual(self.lines("Juan Pérez", "Juan Pérez"), ("Juan Pérez", ""))

    def test_extra_spaces_do_not_break_the_short_slot(self):
        self.assertEqual(
            self.lines("  Juan   Pérez ", "  Consulta  "),
            ("Juan Pérez", "Consulta"),
        )


if __name__ == "__main__":
    unittest.main()
