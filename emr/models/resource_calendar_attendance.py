##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResourceCalendarAttendance(models.Model):
    """Una franja de la agenda del profesional.

    Odoo ya trae día, hora de inicio y hora de fin. Lo que agregamos es lo que
    convierte una franja en turnos: cuánto dura cada uno, de qué modalidad son
    y en qué locación se atienden.

    La duración es de la franja y no del profesional: un mismo médico atiende
    consultorio de 15 minutos un día y endoscopía de 45 otro.
    """

    _inherit = "resource.calendar.attendance"

    slot_duration = fields.Integer(
        "Duración del turno (min)",
        default=15,
        help="Cada cuántos minutos se genera un turno dentro de esta franja.",
    )
    slot_type = fields.Selection(
        [("scheduled", "Turno programado"), ("open", "Franja variable")],
        string="Modalidad",
        default="scheduled",
        help="Programado genera un hueco por intervalo. Variable genera una "
        "ventana abierta a la que se van agregando pacientes.",
    )
    location_id = fields.Many2one("emr.location", string="Locación")
