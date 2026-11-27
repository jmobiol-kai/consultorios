##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    veterinary_kind = fields.Selection(
        [
            ("medicine", "Medicamento"),
            ("accessory", "Accesorio"),
            ("food", "Alimento balanceado"),
            ("service", "Práctica / servicio"),
        ],
        string="Rubro veterinario",
        index=True,
    )

    @api.onchange("veterinary_kind")
    def _onchange_veterinary_kind(self):
        mapping = {
            "medicine": "emr_veterinary.product_category_medicine",
            "accessory": "emr_veterinary.product_category_accessory",
            "food": "emr_veterinary.product_category_food",
            "service": "emr_veterinary.product_category_service",
        }
        xmlid = mapping.get(self.veterinary_kind)
        if xmlid:
            category = self.env.ref(xmlid, raise_if_not_found=False)
            if category:
                self.categ_id = category
