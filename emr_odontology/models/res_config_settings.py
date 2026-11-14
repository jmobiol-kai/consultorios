##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models

from .dental_profile import DENTAL_PROFILE_PARAM


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    emr_odontology_dental_profile = fields.Boolean(
        string="Perfil odontológico",
        config_parameter=DENTAL_PROFILE_PARAM,
        help="Oculta del menú medicamentos, alergias y rendir a un "
        "profesional. No borra esas funciones: al apagarlo vuelven a verse.",
    )

    def set_values(self):
        super().set_values()
        # El menú cachea por usuario. El perfil no está en esa clave.
        self.env.registry.clear_cache()
