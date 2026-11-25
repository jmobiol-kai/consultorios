##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from datetime import timedelta

from odoo import _, api, fields, models


class EmrPetPrevention(models.Model):
    """Vacuna o desparasitación, con la próxima dosis y su recordatorio."""

    _name = "emr.pet.prevention"
    _description = "Vacuna o desparasitación"
    _inherit = "emr.veterinary.signed.mixin"
    _order = "date desc, id desc"
    _emr_vet_signed_ok = {"reminder_sent", "activity_id"}

    pet_id = fields.Many2one(
        "emr.pet", required=True, ondelete="cascade", index=True
    )
    kind = fields.Selection(
        [
            ("vaccine", "Vacuna"),
            ("deworming", "Desparasitación"),
        ],
        string="Tipo",
        required=True,
        default="vaccine",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        required=True,
        domain="[('veterinary_kind', 'in', ('medicine', 'accessory'))]",
    )
    lot_id = fields.Many2one(
        "stock.lot",
        string="Lote",
        domain="[('product_id', '=', product_id)]",
    )
    expiration_date = fields.Datetime(
        related="lot_id.expiration_date", string="Vencimiento"
    )
    date = fields.Date("Fecha", required=True, default=fields.Date.context_today)
    next_date = fields.Date("Próxima dosis")
    encounter_id = fields.Many2one(
        "emr.encounter.veterinary",
        string="Consulta",
        ondelete="set null",
        index=True,
    )
    activity_id = fields.Many2one("mail.activity", string="Recordatorio", copy=False)
    reminder_sent = fields.Boolean(copy=False)
    note = fields.Char("Nota")
    company_id = fields.Many2one(related="pet_id.company_id", store=True)

    @api.depends("kind", "product_id.display_name", "date")
    def _compute_display_name(self):
        labels = dict(self._fields["kind"]._description_selection(self.env))
        for line in self:
            kind = labels.get(line.kind, "")
            line.display_name = "%s %s" % (kind, line.product_id.display_name or "")

    def _emr_vet_encounter(self):
        self.ensure_one()
        return self.encounter_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("encounter_id") and not vals.get("pet_id"):
                encounter = self.env["emr.encounter.veterinary"].browse(vals["encounter_id"])
                vals["pet_id"] = encounter.pet_id.id
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if "next_date" in vals and not self.env.context.get("emr_vet_reminder_write"):
            for line in self:
                if line.activity_id:
                    line.activity_id.unlink()
                if line.reminder_sent or line.activity_id:
                    line.with_context(emr_vet_reminder_write=True).write(
                        {"reminder_sent": False, "activity_id": False}
                    )
        return res

    @api.model
    def _cron_send_reminders(self):
        raw = self.env["ir.config_parameter"].sudo().get_param(
            "emr_veterinary.reminder_days", "7"
        )
        try:
            lead = int(raw)
        except (TypeError, ValueError):
            lead = 7
        today = fields.Date.context_today(self)
        horizon = today + timedelta(days=max(lead, 0))
        lines = self.search(
            [
                ("next_date", "!=", False),
                ("next_date", "<=", horizon),
                ("reminder_sent", "=", False),
                ("pet_id.deceased", "=", False),
                ("pet_id.active", "=", True),
            ]
        )
        lines._create_reminder_activity()
        return True

    def _create_reminder_activity(self):
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        model_id = self.env["ir.model"]._get_id("emr.pet")
        labels = dict(self._fields["kind"]._description_selection(self.env))
        for line in self:
            user = line.pet_id._reminder_user()
            kind = labels.get(line.kind, "")
            activity = self.env["mail.activity"].sudo().create(
                {
                    "res_model_id": model_id,
                    "res_id": line.pet_id.id,
                    "activity_type_id": activity_type.id,
                    "user_id": user.id,
                    "date_deadline": line.next_date,
                    "summary": _(
                        "%(kind)s de %(pet)s: próxima dosis",
                        kind=kind,
                        pet=line.pet_id.name,
                    ),
                    "note": _(
                        "%(kind)s %(product)s. Próxima dosis: %(date)s.",
                        kind=kind,
                        product=line.product_id.display_name,
                        date=line.next_date,
                    ),
                }
            )
            line.with_context(emr_vet_reminder_write=True).write(
                {"activity_id": activity.id, "reminder_sent": True}
            )
        return True
