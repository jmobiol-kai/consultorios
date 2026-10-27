##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.exceptions import UserError


class EmrSlotGenerate(models.TransientModel):
    """Materializa la agenda de uno o varios profesionales.

    Es idempotente: se puede volver a correr sobre el mismo rango sin duplicar
    ni tocar los huecos ya tomados.
    """

    _name = "emr.slot.generate"
    _description = "Generar agenda"

    practitioner_ids = fields.Many2many(
        "res.partner",
        string="Profesionales",
        domain=[("is_practitioner", "=", True)],
        context={"default_is_practitioner": True},
        required=True,
    )
    date_from = fields.Date(
        "Desde", required=True, default=fields.Date.context_today
    )
    date_to = fields.Date("Hasta", required=True)

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "date_to" in fields_list and not res.get("date_to"):
            res["date_to"] = fields.Date.context_today(self) + relativedelta(days=60)
        active_model = self.env.context.get("active_model")
        if active_model == "res.partner" and "practitioner_ids" in fields_list:
            partners = self.env["res.partner"].browse(
                self.env.context.get("active_ids", [])
            )
            res["practitioner_ids"] = [(6, 0, partners.filtered("is_practitioner").ids)]
        return res

    def action_generate(self):
        self.ensure_one()
        if self.date_to < self.date_from:
            raise UserError(_("La fecha de fin no puede ser anterior a la de inicio."))

        Slot = self.env["emr.slot"]
        created = Slot.browse()
        for practitioner in self.practitioner_ids:
            created |= Slot._generate_for_practitioner(
                practitioner, self.date_from, self.date_to
            )

        return {
            "type": "ir.actions.act_window",
            "name": _("Agenda generada"),
            "res_model": "emr.slot",
            "view_mode": "list,kanban,calendar",
            "domain": [("id", "in", created.ids)],
        }
