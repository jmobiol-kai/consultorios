##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Atender ahora: el paciente llegó sin turno y se lo atiende de una.

Es la entrada desde el menú Atención. Desde la ficha del paciente o desde
su odontograma el botón hace lo mismo sin pasar por acá cuando el usuario
es el profesional; este asistente es para cuando hay que elegir paciente o
profesional.

El profesional arranca con el único de la lista, si hay uno solo. Si hay
varios, la primera vez queda vacío y después con el último que ese usuario
confirmó. Cada usuario de Odoo guarda el suyo. El campo se puede cambiar.
"""
from odoo import api, fields, models

from .walkin_default import (
    choose_walkin_practitioner,
    parse_stored_practitioner_id,
    walkin_practitioner_param_key,
)


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
        # Mismo dominio que _practitioner_domain: el default cuenta esa lista.
        domain=[("is_practitioner", "=", True)],
    )

    def _practitioner_domain(self):
        """Quién se puede elegir. Es el dominio del campo Profesional."""
        return [("is_practitioner", "=", True)]

    def _remembered_practitioner_id(self):
        raw = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(walkin_practitioner_param_key(self.env.uid))
        )
        return parse_stored_practitioner_id(raw)

    def _remember_practitioner(self, practitioner):
        """Guarda la elección de este usuario, no la de la clínica."""
        self.env["ir.config_parameter"].sudo().set_param(
            walkin_practitioner_param_key(self.env.uid),
            str(practitioner.id),
        )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "practitioner_id" not in fields_list:
            return res
        Partner = self.env["res.partner"]
        domain = self._practitioner_domain()
        available_count = Partner.search_count(domain)
        sole_id = False
        remembered_id = False
        remembered_allowed = False
        if available_count == 1:
            sole_id = Partner.search(domain, limit=1).id
        elif available_count > 1:
            remembered_id = self._remembered_practitioner_id()
            if remembered_id:
                remembered_allowed = bool(
                    Partner.search_count(domain + [("id", "=", remembered_id)])
                )
        res["practitioner_id"] = choose_walkin_practitioner(
            available_count,
            sole_id=sole_id,
            remembered_id=remembered_id,
            remembered_allowed=remembered_allowed,
        )
        return res

    def action_start(self):
        self.ensure_one()
        if self.practitioner_id:
            self._remember_practitioner(self.practitioner_id)
        return self.partner_id._emr_odontology_walkin(self.practitioner_id)
