##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Lo que se marca en el odontograma de la visita llega al presupuesto.

Cada renglón de la consulta odontológica que es una práctica —una caries a
tratar, una obturación hecha, una endodoncia— se vuelve una línea del turno
(`sale.order`) de esa atención, con un producto de servicio por condición
("Tratamiento de caries", "Obturación", ...) y la descripción de la marca:
"Caries distal pieza 14 (A tratar)". El paréntesis es el nombre del
catálogo; entra al presupuesto por el código (`pending`, `treated`), así
que renombrarlo en Configuración no deja de cobrarlo.

El producto es uno por condición, no uno por pieza y cara: el precio es el
de la práctica, y la pieza y la cara van en la descripción de la línea. Qué
producto corresponde a cada condición lo dice el campo
`odontology_condition` del producto, así que se puede reemplazar por uno
propio con su precio sin tocar código.

No pasa por "Agregar práctica": ese asistente abre otra orden y otra
historia clínica, que es lo que corresponde a una práctica distinta hecha en
el mismo turno. Acá la marca es parte de la misma atención y va en la misma
orden.
"""
from odoo import api, fields, models

# Condición del odontograma -> nombre del producto que se crea si no hay
# ninguno configurado. "Sano" y "Ausente" no son prácticas: no se cobran.
ODONTOLOGY_PRODUCT_NAMES = {
    "caries": "Tratamiento de caries",
    "restoration": "Obturación",
    "crown": "Corona",
    "endodontics": "Endodoncia",
    "implant": "Implante",
    "fracture": "Tratamiento de fractura",
    "extraction": "Extracción",
    "prosthesis": "Prótesis",
    "sealant": "Sellador",
}
# Solo lo que se hizo o hay que hacer. "Presente" es trabajo que el paciente
# ya traía (una corona vieja, por ejemplo) y no se presupuesta.
# La clave es el código, no el nombre de Configuración → Estados de la marca:
# renombrar «A tratar» sigue siendo `pending` y se cobra igual.
BILLABLE_STATUSES = ("pending", "treated")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    odontology_condition = fields.Selection(
        selection="_selection_odontology_condition",
        string="Condición del odontograma",
        index=True,
        help="Si se marca esta condición en el odontograma de una consulta "
        "odontológica, este producto se agrega al turno de la atención.",
    )

    @api.model
    def _selection_odontology_condition(self):
        return self.env["emr.odontogram.mark"]._selection_condition()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    odontology_line_id = fields.Many2one(
        "emr.encounter.odontology.line",
        string="Marca del odontograma",
        index="btree_not_null",
        ondelete="set null",
        copy=False,
        readonly=True,
    )
