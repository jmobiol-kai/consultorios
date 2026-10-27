##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    emr_whatsapp_confirmation_delay = fields.Integer(
        "Demora del aviso de confirmación (min)",
        default=15,
        help="Cuánto espera el sistema antes de mandarle al paciente la "
        "confirmación del turno. Es la ventana para corregir o cancelar sin "
        "que el paciente reciba nada: un aviso enviado no se puede desenviar. "
        "En cero se manda en la primera corrida del cron.",
    )
    emr_whatsapp_reminder_hours = fields.Integer(
        "Recordatorio, horas antes",
        default=24,
        help="Cuántas horas antes del turno se manda el recordatorio. En cero "
        "no se manda ninguno.",
    )
    emr_whatsapp_confirmation_template_id = fields.Many2one(
        "whatsapp.template",
        string="Plantilla de confirmación",
        domain="[('model', '=', 'sale.order')]",
    )
    emr_whatsapp_reminder_template_id = fields.Many2one(
        "whatsapp.template",
        string="Plantilla de recordatorio",
        domain="[('model', '=', 'sale.order')]",
    )
