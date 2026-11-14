##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Fin del turno y color del profesional, para el calendario.

Los turnos viejos no tenían hora de fin. Si están atados a un hueco,
el fin es el del hueco. Si no, media hora después del inicio. Cada
profesional recibe un color estable a partir de su id.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        UPDATE sale_order AS so
           SET appointment_stop = slot.stop
          FROM emr_slot AS slot
         WHERE slot.order_id = so.id
           AND so.is_appointment
           AND so.appointment_stop IS NULL
           AND slot.stop IS NOT NULL
        """
    )
    cr.execute(
        """
        UPDATE sale_order
           SET appointment_stop = appointment_start + interval '30 minutes'
         WHERE is_appointment
           AND appointment_start IS NOT NULL
           AND appointment_stop IS NULL
        """
    )
    cr.execute(
        """
        UPDATE res_partner
           SET emr_calendar_color = (id % 11) + 1
         WHERE is_practitioner
           AND COALESCE(emr_calendar_color, 0) = 0
        """
    )
    _logger.info("emr: turnos con hora de fin y colores de profesional.")
