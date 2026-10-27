##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ProductTemplate(models.Model):
    """La práctica es un producto.

    Los dos campos propios son los que la convierten en una práctica médica:
    qué historia clínica genera y qué se factura al hacerla.
    """

    _inherit = "product.template"

    is_medical_procedure = fields.Boolean("Es una práctica", index=True)
    encounter_type_id = fields.Many2one(
        "emr.encounter.type",
        string="Tipo de historia clínica",
        help="Historia clínica que se abre al atender un turno de esta "
        "práctica. Es la regla que decide qué tiene que llenar el profesional.",
    )
    order_template_id = fields.Many2one(
        "sale.order.template",
        string="Plantilla de la práctica",
        help="Opcional. Si la práctica lleva insumos o anestesia, la plantilla "
        "trae todas las líneas. Si está vacía se agrega solo este producto.",
    )
