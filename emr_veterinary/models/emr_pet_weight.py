##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class EmrPetWeight(models.Model):
    _name = "emr.pet.weight"
    _description = "Peso de la mascota"
    _inherit = "emr.veterinary.signed.mixin"
    _order = "date desc, id desc"

    pet_id = fields.Many2one(
        "emr.pet", string="Mascota", required=True, ondelete="cascade", index=True
    )
    date = fields.Date("Fecha", required=True, default=fields.Date.context_today)
    weight = fields.Float("Peso (kg)", required=True, digits=(6, 3))
    encounter_id = fields.Many2one(
        "emr.encounter.veterinary",
        string="Consulta",
        ondelete="cascade",
        index=True,
    )
    note = fields.Char("Nota")
    company_id = fields.Many2one(related="pet_id.company_id", store=True)

    @api.depends("date", "weight", "pet_id.name")
    def _compute_display_name(self):
        for line in self:
            line.display_name = "%s · %s kg" % (line.date or "", line.weight)

    def _emr_vet_encounter(self):
        self.ensure_one()
        return self.encounter_id
