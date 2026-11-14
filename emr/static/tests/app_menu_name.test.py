"""El mosaico de la aplicación se llama Consultorio.

Sin Odoo: el menú raíz y la traducción es_AR tienen que decir
Consultorio. El nombre técnico del módulo no se toca.
"""
import pathlib
import unittest
import xml.etree.ElementTree as ET

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_MENU = _ROOT / "views" / "emr_menus.xml"
_PO = _ROOT / "i18n" / "es_AR.po"
_MANIFEST = _ROOT / "__manifest__.py"


class AppMenuNameTest(unittest.TestCase):
    def test_root_menu_is_consultorio(self):
        root = ET.parse(_MENU).getroot()
        menu = next(item for item in root.iter("menuitem") if item.get("id") == "menu_emr_root")
        self.assertEqual(menu.get("name"), "Consultorio")
        self.assertEqual(menu.get("web_icon"), "emr,static/description/icon.svg")

    def test_spanish_translation_is_consultorio(self):
        text = _PO.read_text(encoding="utf-8")
        self.assertIn("Language: es_AR", text)
        self.assertIn("model:ir.ui.menu,name:emr.menu_emr_root", text)
        self.assertIn('msgid "Consultorio"', text)
        self.assertIn('msgstr "Consultorio"', text)
        self.assertNotIn("Historia clínica", text)

    def test_apps_list_name_and_technical_name(self):
        manifest = _MANIFEST.read_text(encoding="utf-8")
        self.assertIn('"name": "Consultorio"', manifest)
        self.assertIn('"version": "19.0.1.6.0"', manifest)
        self.assertNotIn("emr_odontology", _MENU.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
