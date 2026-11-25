##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EmrAppointmentBook(models.TransientModel):
    _inherit = "emr.appointment.book"

    pet_id = fields.Many2one(
        "emr.pet",
        string="Mascota",
        domain="[('deceased', '=', False)]",
    )
    pet_owner_id = fields.Many2one(related="pet_id.owner_id")
    partner_id = fields.Many2one(
        domain="['|', ('is_patient', '=', True), ('id', '=', pet_owner_id)]",
    )

    @api.onchange("pet_id")
    def _onchange_pet_id(self):
        if not self.pet_id:
            return
        self.partner_id = self.pet_id.owner_id
        if self.pet_id.deceased:
            return {
                "warning": {
                    "title": _("Mascota fallecida"),
                    "message": _("No se puede agendar un turno para una mascota fallecida."),
                }
            }

    def _prepare_order_vals(self):
        vals = super()._prepare_order_vals()
        if not self.pet_id:
            return vals
        vals["pet_id"] = self.pet_id.id
        vals["partner_id"] = self.pet_id.owner_id.id
        company = vals.get("company_id") or self.env.company.id
        pricelist = self.pet_id.owner_id.with_company(company).property_product_pricelist
        if pricelist:
            vals["pricelist_id"] = pricelist.id
        return vals

    def action_book(self):
        self.ensure_one()
        if self.pet_id and self.pet_id.deceased:
            raise UserError(_("No se puede agendar un turno para una mascota fallecida."))
        if self.pet_id:
            self.partner_id = self.pet_id.owner_id
        return super().action_book()
