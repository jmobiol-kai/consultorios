##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class SaleOrderTemplate(models.Model):
    """La plantilla de venta es el tipo de turno.

    Odoo ya tiene el concepto: un conjunto de líneas con nombre, que se aplica
    de una. Lo único que falta es decir cuáles de esas plantillas son turnos,
    porque una clínica también vende cosas que no lo son.
    """

    _inherit = "sale.order.template"

    is_appointment = fields.Boolean(
        "Es un tipo de turno",
        index=True,
        help="Solo estas plantillas se ofrecen al asignar un turno, y son las "
        "que convierten la orden en una atención con profesional, horario y "
        "historia clínica. Una plantilla que no es turno se vende como "
        "cualquier otra cosa.",
    )
