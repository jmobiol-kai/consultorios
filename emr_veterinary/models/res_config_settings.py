##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    emr_veterinary_auto_validate_delivery = fields.Boolean(
        string="Validar entrega automáticamente con stock",
        default=True,
        help="Al confirmar una venta, si hay stock para todas las líneas "
        "almacenables, la entrega se valida sola. Los pedidos del sitio "
        "se retiran en la clínica y no se validan.",
    )

    @api.model
    def _emr_veterinary_init_auto_validate_delivery(self):
        """Prende el check una sola vez en las compañías ya cargadas."""
        param = self.env["ir.config_parameter"].sudo()
        key = "emr_veterinary.auto_validate_delivery_initialized"
        if param.get_param(key):
            return
        self.search([]).write({"emr_veterinary_auto_validate_delivery": True})
        param.set_param(key, "1")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    emr_veterinary_auto_validate_delivery = fields.Boolean(
        related="company_id.emr_veterinary_auto_validate_delivery",
        readonly=False,
        string="Validar entrega automáticamente con stock",
    )
