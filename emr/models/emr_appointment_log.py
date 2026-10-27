##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class EmrAppointmentLog(models.Model):
    """El recorrido de un turno: qué estado, quién y cuándo.

    Es un registro propio y no seguimiento de campos ni auditoría genérica.
    La consulta real es siempre la misma —el recorrido de este turno— y cuatro
    columnas indexadas por orden la responden mejor que nada más.

    En el sistema que reemplaza, el log no tenía id de turno y había que unirlo
    por hora y profesional. Eso no vuelve a pasar.
    """

    _name = "emr.appointment.log"
    _description = "Recorrido del turno"
    _order = "create_date desc, id desc"

    order_id = fields.Many2one(
        "sale.order", string="Turno", required=True, index=True, ondelete="cascade"
    )
    appointment_state = fields.Selection(
        lambda self: self.env["sale.order"]._fields["appointment_state"].selection,
        string="Estado",
        required=True,
    )
    user_id = fields.Many2one(
        "res.users", string="Usuario", required=True, default=lambda self: self.env.user
    )
