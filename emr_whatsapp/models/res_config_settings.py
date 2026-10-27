##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    emr_whatsapp_confirmation_delay = fields.Integer(
        related="company_id.emr_whatsapp_confirmation_delay", readonly=False,
    )
    emr_whatsapp_reminder_hours = fields.Integer(
        related="company_id.emr_whatsapp_reminder_hours", readonly=False,
    )
    emr_whatsapp_confirmation_template_id = fields.Many2one(
        related="company_id.emr_whatsapp_confirmation_template_id", readonly=False,
    )
    emr_whatsapp_reminder_template_id = fields.Many2one(
        related="company_id.emr_whatsapp_reminder_template_id", readonly=False,
    )
