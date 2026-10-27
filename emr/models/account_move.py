##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class AccountMove(models.Model):
    """El profesional viaja a la factura.

    Sin esto, saber de qué médico es una factura obliga a recorrer la orden y
    el turno en cada consulta.
    """

    _inherit = "account.move"

    practitioner_id = fields.Many2one(
        "res.partner",
        string="Profesional",
        index=True,
        domain=[("is_practitioner", "=", True)],
        context={"default_is_practitioner": True},
    )
    assistant_ids = fields.Many2many(
        "res.partner",
        "emr_move_assistant_rel",
        "move_id",
        "partner_id",
        string="Otros profesionales",
    )
