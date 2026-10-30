##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Atender ahora: el paciente llegó sin turno y se lo atiende de una.

Es la entrada desde el menú Atención. Desde la ficha del paciente o desde
su odontograma el botón hace lo mismo sin pasar por acá cuando el usuario
es el profesional; este asistente es para cuando hay que elegir paciente o
profesional.
"""
from odoo import fields, models


class EmrOdontologyWalkin(models.TransientModel):
    _name = "emr.odontology.walkin"
    _description = "Atender ahora (odontología, sin turno)"

    partner_id = fields.Many2one(
        "res.partner",
        string="Paciente",
        required=True,
        domain=[("is_patient", "=", True)],
        context={"default_is_patient": True, "show_vat": True},
    )
    practitioner_id = fields.Many2one(
        "res.partner",
        string="Profesional",
        required=True,
        domain=[("is_practitioner", "=", True)],
        default=lambda self: self.env["res.partner"]._emr_current_practitioner(),
    )

    def action_start(self):
        self.ensure_one()
        return self.partner_id._emr_odontology_walkin(self.practitioner_id)
