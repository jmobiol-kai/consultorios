##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EmrAppointmentAddon(models.TransientModel):
    """Sumarle una práctica a un turno que ya existe.

    El paciente entró por una consulta y le terminaron haciendo un banding.
    Eso se descubre durante la atención, no al agendar, y hay que poder
    cargarlo sin deshacer nada de lo que ya está.

    Sale una orden nueva colgada del turno, no una línea más en la original:
    son dos atenciones distintas, cada una con su historia clínica y su
    comprobante. Y no ocupa hueco — el paciente ya está adentro.
    """

    _name = "emr.appointment.addon"
    _description = "Agregar una práctica al turno"

    parent_order_id = fields.Many2one(
        "sale.order", string="Turno", required=True, readonly=True,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Paciente",
        related="parent_order_id.partner_id", readonly=True,
    )
    appointment_start = fields.Datetime(
        related="parent_order_id.appointment_start", readonly=True,
    )

    # Editable a propósito: la práctica agregada la hace muchas veces otro
    # profesional, que es justamente el caso que hay que poder registrar.
    practitioner_id = fields.Many2one(
        "res.partner", string="Profesional", required=True,
        domain=[("is_practitioner", "=", True)],
        context={"default_is_practitioner": True},
    )
    location_id = fields.Many2one("emr.location", string="Locación")

    sale_order_template_id = fields.Many2one(
        "sale.order.template", string="Práctica", required=True,
        domain=[("is_appointment", "=", True)],
        help="Qué se le hizo además de lo que estaba agendado.",
    )
    encounter_type_id = fields.Many2one(
        "emr.encounter.type", string="Historia clínica que genera",
        compute="_compute_encounter_type_id",
    )
    note = fields.Text("Nota")

    @api.model
    def default_get(self, fields_list):
        valores = super().default_get(fields_list)
        orden = self.env["sale.order"].browse(
            valores.get("parent_order_id")
            or self.env.context.get("default_parent_order_id")
        )
        if orden:
            valores.setdefault("practitioner_id", orden.practitioner_id.id)
            valores.setdefault("location_id", orden.location_id.id)
        return valores

    @api.depends("sale_order_template_id")
    def _compute_encounter_type_id(self):
        for wiz in self:
            practicas = wiz.sale_order_template_id.sale_order_template_line_ids
            tipos = practicas.product_id.encounter_type_id
            wiz.encounter_type_id = tipos[:1]

    def action_add(self):
        self.ensure_one()
        padre = self.parent_order_id
        if padre.parent_order_id:
            raise UserError(
                _("%s ya es una práctica agregada. La nueva va sobre el turno "
                  "original.", padre.name)
            )

        orden = self.env["sale.order"].create({
            "partner_id": padre.partner_id.id,
            # La misma compañía que el turno original: la práctica agregada es
            # parte de la misma atención. Quién la factura lo decide después
            # `_prepare_invoice`, con el profesional que la hizo.
            "company_id": padre.company_id.id,
            "pricelist_id": padre.pricelist_id.id,
            "is_appointment": True,
            "parent_order_id": padre.id,
            "practitioner_id": self.practitioner_id.id,
            # Sin slot_id: no ocupa un hueco de agenda. El paciente ya está
            # adentro, y bloquear un horario que nadie va a usar ensucia la
            # grilla del día siguiente.
            "location_id": self.location_id.id or padre.location_id.id or False,
            "appointment_start": padre.appointment_start,
            "appointment_mode": padre.appointment_mode,
            "appointment_state": "booked",
            "appointment_priority": padre.appointment_priority,
            "note": self.note or False,
        })
        orden._emr_apply_template(self.sale_order_template_id)

        # Se encadena con el cobro, igual que al asignar: lo habitual es que
        # el paciente esté ahí y se cobre en el momento.
        return orden.action_appointment_confirm()
