##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models


class EmrDemandBook(models.TransientModel):
    """Atender a alguien que llegó sin turno.

    En demanda no hay grilla que mirar: se elige el profesional y el hueco se
    crea en el próximo momento libre. Es la puerta de entrada desde la agenda,
    donde estos profesionales no aparecen justamente porque no tienen huecos
    generados.
    """

    _name = "emr.demand.book"
    _description = "Atender por demanda"

    practitioner_id = fields.Many2one(
        "res.partner",
        string="Profesional",
        required=True,
        domain=[("is_practitioner", "=", True), ("scheduling_method", "=", "walkin")],
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "practitioner_id" in fields_list and not res.get("practitioner_id"):
            candidatos = self.env["res.partner"].search(
                [
                    ("is_practitioner", "=", True),
                    ("scheduling_method", "=", "walkin"),
                ]
            )
            if len(candidatos) == 1:
                res["practitioner_id"] = candidatos.id
        return res

    def action_book(self):
        self.ensure_one()
        slot = self.env["emr.slot"]._create_demand_slot(self.practitioner_id)
        return slot.action_book()
