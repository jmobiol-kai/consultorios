##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_open_odontogram(self):
        """Abre el odontograma del paciente y lo crea si no existe.

        Es uno por paciente. El botón de la ficha es la entrada: no hace
        falta pasar por una visita para ver cómo está la boca.
        """
        self.ensure_one()
        if not self.is_patient:
            raise UserError(_("Solo un paciente tiene odontograma."))
        chart = self.env["emr.odontogram"]._get_or_create(self)
        return {
            "type": "ir.actions.act_window",
            "name": _("Odontograma"),
            "res_model": "emr.odontogram",
            "res_id": chart.id,
            "view_mode": "form",
            "target": "current",
        }
