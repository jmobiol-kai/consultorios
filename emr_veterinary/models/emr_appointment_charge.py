##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class EmrAppointmentCharge(models.TransientModel):
    _inherit = "emr.appointment.charge"

    pet_id = fields.Many2one(related="order_id.pet_id", string="Mascota")
