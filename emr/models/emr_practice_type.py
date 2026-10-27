##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class EmrPracticeType(models.Model):
    """Tipo de práctica, como registro clínico.

    No confundir con la práctica que se factura, que es un producto de
    servicio y viaja en la línea del pedido. Son dos datos parecidos y
    distintos: la línea del pedido dice **qué se cobró** y puede cambiar,
    anularse o no existir; esto dice **qué se le hizo al paciente**, y no se
    toca después.
    """

    _name = "emr.practice.type"
    _description = "Tipo de práctica"
    _order = "name"

    name = fields.Char(required=True, index=True)
    code = fields.Char(index=True)
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint(
        "UNIQUE (name)", "Ya hay un tipo de práctica con ese nombre."
    )
