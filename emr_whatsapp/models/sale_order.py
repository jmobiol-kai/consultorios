##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Estados en los que ya no tiene sentido avisarle nada al paciente.
SIN_AVISO = ("cancelled", "void", "no_show")


class SaleOrder(models.Model):
    """El turno, con sus avisos por WhatsApp.

    Nada se envía en el momento de asignar. El turno queda **encolado** y un
    cron lo manda unos minutos después. Dos razones, y la segunda importa
    tanto como la primera:

    - Da tiempo a corregir. En un mostrador se asigna, se descubre que era
      otro día y se corrige; un aviso ya enviado no se puede desenviar.
    - Saca el envío de la transacción del turno. Si WhatsApp está caído o la
      plantilla no está aprobada, el turno se asigna igual. Un aviso es un
      accesorio y no puede impedir atender a alguien.
    """

    _inherit = "sale.order"

    whatsapp_confirmation_state = fields.Selection(
        [
            ("none", "Sin encolar"),
            ("queued", "En cola"),
            ("sent", "Enviado"),
            ("skipped", "No corresponde"),
            ("failed", "Falló"),
        ],
        string="Confirmación por WhatsApp",
        default="none",
        copy=False,
        index=True,
        readonly=True,
    )
    whatsapp_confirmation_queued_at = fields.Datetime(
        "Encolado", copy=False, readonly=True,
        help="Desde este momento se cuenta la demora antes de enviar.",
    )
    whatsapp_reminder_state = fields.Selection(
        [
            ("none", "Pendiente"),
            ("sent", "Enviado"),
            ("skipped", "No corresponde"),
            ("failed", "Falló"),
        ],
        string="Recordatorio por WhatsApp",
        default="none",
        copy=False,
        index=True,
        readonly=True,
    )
    whatsapp_error = fields.Char("Motivo del fallo", copy=False, readonly=True)

    # ------------------------------------------------------------------
    # Encolar
    # ------------------------------------------------------------------
    def _emr_queue_whatsapp_confirmation(self):
        """Deja el turno listo para que el cron avise. No envía nada."""
        aptos = self.filtered(
            lambda o: o.is_appointment
            and o.whatsapp_confirmation_state in ("none", "failed")
            and o.appointment_state not in SIN_AVISO
        )
        if aptos:
            aptos.write({
                "whatsapp_confirmation_state": "queued",
                "whatsapp_confirmation_queued_at": fields.Datetime.now(),
                "whatsapp_error": False,
            })
        return True

    def action_whatsapp_queue_now(self):
        """Vuelve a encolar el aviso, a mano.

        Sirve cuando el paciente dio un teléfono nuevo, o cuando el envío
        falló y se corrigió la causa.
        """
        self.ensure_one()
        if not self.is_appointment:
            raise UserError(_("Esto no es un turno."))
        self.write({
            "whatsapp_confirmation_state": "queued",
            "whatsapp_confirmation_queued_at": fields.Datetime.now(),
            "whatsapp_error": False,
        })
        return True

    def action_whatsapp_cancel_queued(self):
        """Saca el turno de la cola antes de que salga el aviso."""
        self.ensure_one()
        if self.whatsapp_confirmation_state != "queued":
            raise UserError(_("Este turno no tiene un aviso en cola."))
        self.write({"whatsapp_confirmation_state": "skipped"})
        return True

    # ------------------------------------------------------------------
    # Los crons
    # ------------------------------------------------------------------
    @api.model
    def _cron_whatsapp_confirmations(self):
        """Manda las confirmaciones que ya cumplieron su demora."""
        ahora = fields.Datetime.now()
        candidatos = self.search([
            ("whatsapp_confirmation_state", "=", "queued"),
            ("is_appointment", "=", True),
        ])
        for compania, turnos in self._emr_group_by_company(candidatos).items():
            demora = timedelta(minutes=compania.emr_whatsapp_confirmation_delay or 0)
            maduros = turnos.filtered(
                lambda o: o.whatsapp_confirmation_queued_at
                and o.whatsapp_confirmation_queued_at + demora <= ahora
            )
            # El turno pudo cancelarse mientras esperaba: era el punto de
            # esperar.
            vencidos = maduros.filtered(
                lambda o: o.appointment_state in SIN_AVISO
            )
            if vencidos:
                vencidos.write({"whatsapp_confirmation_state": "skipped"})
            self._emr_send_whatsapp(
                maduros - vencidos,
                compania.emr_whatsapp_confirmation_template_id,
                "whatsapp_confirmation_state",
            )

    @api.model
    def _cron_whatsapp_reminders(self):
        """Manda el recordatorio a los turnos que caen dentro de la ventana."""
        ahora = fields.Datetime.now()
        for compania in self.env["res.company"].search([]):
            horas = compania.emr_whatsapp_reminder_hours
            if not horas:
                continue
            turnos = self.search([
                ("company_id", "=", compania.id),
                ("is_appointment", "=", True),
                ("whatsapp_reminder_state", "=", "none"),
                ("appointment_start", ">=", ahora),
                ("appointment_start", "<=", ahora + timedelta(hours=horas)),
            ])
            vencidos = turnos.filtered(
                lambda o: o.appointment_state in SIN_AVISO
            )
            if vencidos:
                vencidos.write({"whatsapp_reminder_state": "skipped"})
            self._emr_send_whatsapp(
                turnos - vencidos,
                compania.emr_whatsapp_reminder_template_id,
                "whatsapp_reminder_state",
            )

    # ------------------------------------------------------------------
    # El envío
    # ------------------------------------------------------------------
    @api.model
    def _emr_group_by_company(self, turnos):
        agrupado = {}
        for turno in turnos:
            agrupado.setdefault(turno.company_id, self.browse())
            agrupado[turno.company_id] |= turno
        return agrupado

    @api.model
    def _emr_send_whatsapp(self, turnos, plantilla, campo_estado):
        """Manda la plantilla a esos turnos, en lote.

        Es la forma que usa Enterprise en whatsapp_calendar: el composer en
        modo lote encola los mensajes y los despacha su propio cron. Acá no se
        habla con la API de Meta.

        Cualquier error queda registrado en el turno y no se propaga: esto
        corre en un cron y una plantilla sin aprobar no puede frenar los
        avisos de los demás.
        """
        if not turnos:
            return
        if not plantilla:
            turnos.write({
                campo_estado: "failed",
                "whatsapp_error": _("No hay plantilla configurada."),
            })
            _logger.warning("EMR WhatsApp: sin plantilla para %s", campo_estado)
            return
        if plantilla.status != "approved":
            turnos.write({
                campo_estado: "failed",
                "whatsapp_error": _(
                    "La plantilla %(nombre)s está en estado %(estado)s. Meta "
                    "tiene que aprobarla antes de poder enviarla.",
                    nombre=plantilla.name, estado=plantilla.status,
                ),
            })
            return

        sin_telefono = turnos.filtered(lambda o: not o.partner_id.phone)
        if sin_telefono:
            sin_telefono.write({
                campo_estado: "skipped",
                "whatsapp_error": _("El paciente no tiene teléfono."),
            })
        enviables = turnos - sin_telefono
        if not enviables:
            return

        try:
            self.env["whatsapp.composer"].create({
                "batch_mode": True,
                "res_model": "sale.order",
                "res_ids": str(enviables.ids),
                "wa_template_id": plantilla.id,
            })._send_whatsapp_template(force_send_by_cron=True)
        except Exception as error:  # noqa: BLE001
            enviables.write({
                campo_estado: "failed",
                "whatsapp_error": str(error)[:200],
            })
            _logger.exception("EMR WhatsApp: falló el envío en lote")
            return

        enviables.write({campo_estado: "sent", "whatsapp_error": False})
        _logger.info("EMR WhatsApp: %d avisos encolados (%s)",
                     len(enviables), campo_estado)
