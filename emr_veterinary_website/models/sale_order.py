##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    emr_website_ip = fields.Char(
        "IP del sitio",
        copy=False,
        index=True,
        help="La guarda el pedido de turno público, para frenar ráfagas.",
    )
