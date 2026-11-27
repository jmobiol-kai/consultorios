##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class EmrEncounter(models.Model):
    _inherit = "emr.encounter"

    pet_id = fields.Many2one(
        "emr.pet",
        string="Mascota",
        index=True,
        ondelete="restrict",
    )

    @api.depends("partner_id", "encounter_type_id", "date", "pet_id", "pet_id.name")
    def _compute_display_name(self):
        super()._compute_display_name()
        for enc in self.filtered("pet_id"):
            enc.display_name = "%s - %s" % (
                enc.encounter_type_id.name or "",
                enc.pet_id.name or "",
            )

    def _patient_history_domain(self, partner_id, exclude_id=None):
        domain = super()._patient_history_domain(partner_id, exclude_id)
        pet_id = self.env.context.get("emr_pet_id")
        if pet_id:
            domain.append(("pet_id", "=", int(pet_id)))
        return domain

    def _vet_align_owner(self, vals):
        pet_id = vals.get("pet_id")
        if not pet_id:
            return vals
        pet = self.env["emr.pet"].browse(pet_id)
        if not pet.owner_id:
            raise UserError(_("La mascota %(name)s no tiene dueño.", name=pet.display_name))
        vals = dict(vals)
        vals["partner_id"] = pet.owner_id.id
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._vet_align_owner(vals) for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("pet_id"):
            pet = self.env["emr.pet"].browse(vals["pet_id"])
            vals = dict(vals, partner_id=pet.owner_id.id)
        return super().write(vals)


class EmrEncounterVeterinary(models.Model):
    """Consulta veterinaria. Delega en emr.encounter, como el resto de los tipos."""

    _name = "emr.encounter.veterinary"
    _description = "Consulta veterinaria"
    _inherit = "emr.encounter.mixin"
    _inherits = {"emr.encounter": "encounter_id"}

    reason = fields.Text("Motivo de consulta")
    anamnesis = fields.Text("Anamnesis")
    examination = fields.Text("Examen clínico")
    temperature = fields.Float("Temperatura (°C)", digits=(4, 1))
    weight = fields.Float("Peso (kg)", digits=(6, 3))
    diagnosis = fields.Text("Diagnóstico")
    evolution = fields.Text("Evolución")
    consumption_line_ids = fields.One2many(
        "emr.veterinary.consumption.line", "encounter_id", string="Medicación e insumos"
    )
    prevention_ids = fields.One2many(
        "emr.pet.prevention", "encounter_id", string="Vacunas y desparasitación"
    )
    prescription_ids = fields.One2many(
        "emr.veterinary.prescription", "encounter_id", string="Recetas"
    )

    @api.constrains("pet_id")
    def _check_pet(self):
        for rec in self:
            if not rec.pet_id:
                raise ValidationError(
                    _("La consulta veterinaria tiene que indicar la mascota.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        dead = records.filtered("pet_id.deceased")
        if dead:
            raise UserError(
                _(
                    "No se abre una consulta para %(name)s porque figura como fallecido.",
                    name=dead[0].pet_id.name,
                )
            )
        records._sync_weight_history()
        return records

    def write(self, vals):
        res = super().write(vals)
        if {"weight", "date", "pet_id"} & set(vals):
            self._sync_weight_history()
        return res

    def _sync_weight_history(self):
        Weight = self.env["emr.pet.weight"]
        for rec in self:
            existing = Weight.search([("encounter_id", "=", rec.id)], limit=1)
            if not rec.weight or not rec.pet_id:
                if existing:
                    existing.unlink()
                continue
            vals = {
                "pet_id": rec.pet_id.id,
                "date": fields.Date.to_date(rec.date) or fields.Date.context_today(rec),
                "weight": rec.weight,
                "encounter_id": rec.id,
            }
            if existing:
                existing.write(vals)
            else:
                Weight.create(vals)

    def _consumption_order(self):
        """El pedido al que se le cargan los insumos: el turno, o uno nuevo del dueño."""
        self.ensure_one()
        order = self.order_id
        if order and order.state != "cancel" and not order.locked:
            return order
        return self.env["sale.order"].sudo().create(
            {
                "partner_id": self.partner_id.id,
                "pet_id": self.pet_id.id,
                "company_id": self.company_id.id,
                "origin": self.display_name,
                "is_appointment": False,
            }
        )

    def _apply_consumption(self):
        self.ensure_one()
        orders = self.env["sale.order"]
        for line in self.consumption_line_ids:
            if line.to_invoice and not line.sale_line_id:
                orders |= line._create_sale_line().order_id
            if line.product_id.is_storable and not line.stock_move_id:
                line._create_stock_move()
        for order in orders.filtered(lambda item: item.state in ("sale", "done") and not item.locked):
            order.sudo()._create_invoices()
        return True

    def action_close(self):
        for rec in self:
            rec._sync_weight_history()
            rec._apply_consumption()
        return super().action_close()
