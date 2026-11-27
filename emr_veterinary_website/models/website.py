##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models
from odoo.fields import Domain


class Website(models.Model):
    _inherit = "website"

    def sale_product_domain(self):
        """La tienda publica medicamento, accesorio y alimento.

        Un servicio o una práctica, aunque alguien la publique, no se vende
        por la web. El mostrador sigue usando el pedido de Ventas.
        """
        return Domain.AND([
            super().sale_product_domain(),
            [("veterinary_kind", "in", ["medicine", "accessory", "food"])],
        ])
