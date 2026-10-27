##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class EmrAppointmentBook(models.TransientModel):
    """El asistente de asignación, que además encola el aviso.

    Se engancha acá y no en `sale.order.create` a propósito. Crear una orden
    de turno pasa también por la migración y por los scripts, y ahí un
    disparador ciego mandaría noventa mil WhatsApps. El aviso corresponde
    cuando alguien asigna un turno desde el mostrador, que es exactamente lo
    que hace este asistente.
    """

    _inherit = "emr.appointment.book"

    def action_book(self):
        resultado = super().action_book()
        # El turno recién creado es el del hueco, o el último del paciente
        # cuando la asignación fue sin hueco.
        turno = self.slot_id.order_id
        if not turno:
            turno = self.env["sale.order"].search(
                [("is_appointment", "=", True),
                 ("partner_id", "=", self.partner_id.id)],
                order="id desc", limit=1,
            )
        if turno:
            turno._emr_queue_whatsapp_confirmation()
        return resultado
