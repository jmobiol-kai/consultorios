##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Esconde menús de emr que un consultorio dental no usa a diario.

`load_menus` de Odoo 19 consulta `_load_menus_blacklist`. Con el perfil
odontológico prendido, medicamentos, alergias y rendir a un profesional
no entran en el menú. Los modelos y las acciones siguen: otra
especialidad apaga el perfil en Ajustes y los vuelve a ver. No se
reescriben los grupos del menú de emr.
"""
from odoo import api, models

from .dental_profile import DENTAL_HIDDEN_MENU_XMLIDS, DENTAL_PROFILE_PARAM, dental_profile_enabled


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def _load_menus_blacklist(self):
        hidden = list(super()._load_menus_blacklist())
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(DENTAL_PROFILE_PARAM, "True")
        )
        if not dental_profile_enabled(value):
            return hidden
        for xmlid in DENTAL_HIDDEN_MENU_XMLIDS:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu:
                hidden.append(menu.id)
        return hidden
