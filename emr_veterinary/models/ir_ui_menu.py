##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class IrUiMenu(models.Model):
    """En una base veterinaria la app de uso es Veterinaria.

    Consultorio sigue instalado —es la base de turnos e historia— pero el
    menú raíz no se ofrece al personal. Lo ve solo quien administra el
    sistema. Al desinstalar este módulo el override desaparece y Consultorio
    vuelve a verse como en una base odontológica.
    """

    _inherit = "ir.ui.menu"

    @api.model
    def _visible_menu_ids(self, debug=False):
        visible = super()._visible_menu_ids(debug=debug)
        if self.env.user.has_group("base.group_system"):
            return visible
        root = self.env.ref("emr.menu_emr_root", raise_if_not_found=False)
        if not root:
            return visible
        hidden = set(self.search([("id", "child_of", root.id)]).ids)
        return frozenset(set(visible) - hidden)
