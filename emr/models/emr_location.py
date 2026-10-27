##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class EmrLocation(models.Model):
    """Espacio físico donde se atiende: un consultorio, una sala.

    No es una stock.location: son lugares de atención, no de inventario.
    """

    _name = "emr.location"
    _description = "Locación de atención"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    partner_id = fields.Many2one("res.partner", string="Dirección")
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    active = fields.Boolean(default=True)
