##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models


class EmrVeterinaryPrescription(models.Model):
    _name = "emr.veterinary.prescription"
    _description = "Receta veterinaria"
    _inherit = "emr.veterinary.signed.mixin"
    _order = "date desc, id desc"

    encounter_id = fields.Many2one(
        "emr.encounter.veterinary",
        string="Consulta",
        required=True,
        ondelete="cascade",
        index=True,
    )
    pet_id = fields.Many2one(related="encounter_id.pet_id", store=True)
    owner_id = fields.Many2one(related="encounter_id.partner_id", string="Dueño", store=True)
    practitioner_id = fields.Many2one(related="encounter_id.practitioner_id", store=True)
    date = fields.Date("Fecha", required=True, default=fields.Date.context_today)
    indications = fields.Text("Indicaciones")
    line_ids = fields.One2many(
        "emr.veterinary.prescription.line", "prescription_id", string="Medicamentos"
    )
    company_id = fields.Many2one(related="encounter_id.company_id", store=True)

    @api.depends("date", "pet_id.name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = _("Receta %(date)s · %(pet)s", date=rec.date or "", pet=rec.pet_id.name or "")

    def _emr_vet_encounter(self):
        self.ensure_one()
        return self.encounter_id

    def action_print(self):
        self.ensure_one()
        return self.env.ref("emr_veterinary.action_report_prescription").report_action(self)


class EmrVeterinaryPrescriptionLine(models.Model):
    _name = "emr.veterinary.prescription.line"
    _description = "Línea de receta"
    _inherit = "emr.veterinary.signed.mixin"
    _order = "id"

    prescription_id = fields.Many2one(
        "emr.veterinary.prescription",
        string="Receta",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        domain="[('veterinary_kind', 'in', ('medicine', 'food', 'accessory'))]",
    )
    name = fields.Char("Medicamento", required=True)
    dosage = fields.Char("Dosis")
    instructions = fields.Char("Cómo darlo")

    @api.depends("name", "dosage")
    def _compute_display_name(self):
        for line in self:
            line.display_name = " · ".join(
                bit for bit in (line.name, line.dosage) if bit
            )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id and not self.name:
            self.name = self.product_id.display_name

    def _emr_vet_encounter(self):
        self.ensure_one()
        return self.prescription_id.encounter_id
