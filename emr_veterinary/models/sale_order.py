##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain

from odoo.addons.emr.models.calendar_label import appointment_calendar_lines


class SaleOrder(models.Model):
    _inherit = "sale.order"

    pet_id = fields.Many2one(
        "emr.pet",
        string="Mascota",
        index=True,
        ondelete="restrict",
        tracking=False,
    )

    @api.depends(
        "partner_id.name",
        "name",
        "is_appointment",
        "sale_order_template_id.name",
        "order_line.product_id.name",
        "order_line.product_id.is_medical_procedure",
        "pet_id.name",
    )
    def _compute_appointment_calendar_title(self):
        super()._compute_appointment_calendar_title()
        for order in self.filtered(lambda item: item.is_appointment and item.pet_id):
            title, subtitle = appointment_calendar_lines(
                order.pet_id.name,
                order.appointment_calendar_subtitle,
            )
            order.appointment_calendar_title = title
            order.appointment_calendar_subtitle = subtitle

    def _emr_appointment_partner_is_valid(self):
        self.ensure_one()
        if self.pet_id:
            return bool(self.partner_id)
        return super()._emr_appointment_partner_is_valid()

    @api.onchange("pet_id")
    def _onchange_vet_pet_id(self):
        if not self.pet_id:
            return
        self.partner_id = self.pet_id.owner_id
        pricelist = self.pet_id.owner_id.property_product_pricelist
        if pricelist:
            self.pricelist_id = pricelist

    def _onchange_partner_id_insurer_pricelist(self):
        if self.pet_id:
            pricelist = self.partner_id.property_product_pricelist
            if pricelist:
                self.pricelist_id = pricelist
            return
        return super()._onchange_partner_id_insurer_pricelist()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            pet_id = vals.get("pet_id")
            if not pet_id:
                continue
            pet = self.env["emr.pet"].browse(pet_id)
            if vals.get("is_appointment") and pet.deceased:
                raise UserError(
                    _(
                        "No se puede agendar un turno para %(name)s porque figura como fallecido.",
                        name=pet.name,
                    )
                )
            if pet.owner_id:
                vals["partner_id"] = pet.owner_id.id
        return super().create(vals_list)

    def _open_encounter(self):
        self.ensure_one()
        if self.pet_id and not self.encounter_id:
            return super(
                SaleOrder, self.with_context(default_pet_id=self.pet_id.id)
            )._open_encounter()
        return super()._open_encounter()

    def _get_product_catalog_domain(self):
        domain = super()._get_product_catalog_domain()
        if self.env.context.get("emr_veterinary_counter_sale"):
            domain &= Domain(
                "veterinary_kind", "in", ("medicine", "accessory", "food")
            )
        return domain
