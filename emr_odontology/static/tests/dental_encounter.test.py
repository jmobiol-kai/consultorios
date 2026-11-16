"""Con el perfil odontológico, la consulta genérica abre el odontograma.

Sin Odoo: la regla no toca una especialidad que ya tiene su modelo.
"""
import importlib.util
import pathlib
import unittest

_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "models"
    / "dental_encounter.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("dental_encounter", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DentalEncounterTest(unittest.TestCase):
    def setUp(self):
        self.mod = _load()

    def test_dental_profile_turns_the_generic_consultation_into_odontology(self):
        self.assertEqual(
            self.mod.preferred_encounter_model(
                "emr.encounter.consultation", True
            ),
            "emr.encounter.odontology",
        )
        self.assertEqual(
            self.mod.preferred_encounter_model("", True),
            "emr.encounter.odontology",
        )

    def test_another_specialty_stays(self):
        self.assertEqual(
            self.mod.preferred_encounter_model(
                "emr.encounter.endoscopy", True
            ),
            "emr.encounter.endoscopy",
        )
        self.assertEqual(
            self.mod.preferred_encounter_model(
                "emr.encounter.odontology", True
            ),
            "emr.encounter.odontology",
        )

    def test_without_the_dental_profile_the_generic_consultation_stays(self):
        self.assertEqual(
            self.mod.preferred_encounter_model(
                "emr.encounter.consultation", False
            ),
            "emr.encounter.consultation",
        )

    def test_odontology_is_not_forced_when_the_model_is_missing(self):
        self.assertEqual(
            self.mod.preferred_encounter_model(
                "emr.encounter.consultation", True, dental_available=False
            ),
            "emr.encounter.consultation",
        )


if __name__ == "__main__":
    unittest.main()
