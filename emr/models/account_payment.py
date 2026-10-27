##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class AccountPayment(models.Model):
    """El profesional viaja hasta el cobro.

    Es la pieza que sostiene la liquidación: juntar lo cobrado a nombre de un
    profesional en un período es un filtro sobre este campo, y no un recorrido
    de pago a factura a orden a turno por cada cobro.
    """

    _inherit = "account.payment"

    practitioner_id = fields.Many2one(
        "res.partner",
        string="Profesional",
        index=True,
        domain=[("is_practitioner", "=", True)],
        context={"default_is_practitioner": True},
    )

    # ------------------------------------------------------------------
    # Rendición
    # ------------------------------------------------------------------
    emr_settled = fields.Boolean(
        "Rendido",
        copy=False,
        index=True,
        help="Este cobro ya se le rindió al profesional. Marcarlo es lo que "
        "impide pagarle dos veces lo mismo.",
    )
    emr_settlement_id = fields.Many2one(
        "account.payment",
        string="Pago de la rendición",
        copy=False,
        index=True,
        help="El pago con el que se le rindió este cobro al profesional.",
    )
    emr_settled_payment_ids = fields.One2many(
        "account.payment",
        "emr_settlement_id",
        string="Cobros rendidos",
        help="Los cobros que este pago le rinde al profesional.",
    )
