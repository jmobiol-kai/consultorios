##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EmrAppointmentBook(models.TransientModel):
    """Asignarle un paciente a un hueco de agenda.

    Es el paso que convierte disponibilidad en demanda: hasta acá había un
    hueco libre; a partir de acá hay una orden de venta en borrador, que es el
    turno. Todavía no se factura ni se cobra — eso pasa cuando el paciente
    llega.
    """

    _name = "emr.appointment.book"
    _description = "Asignar turno"

    slot_id = fields.Many2one("emr.slot", string="Hueco", readonly=True)

    practitioner_id = fields.Many2one(
        "res.partner",
        string="Profesional",
        required=True,
        domain=[("is_practitioner", "=", True)],
        context={"default_is_practitioner": True},
    )
    start = fields.Datetime("Fecha y hora", required=True)
    location_id = fields.Many2one("emr.location", string="Locación")

    partner_id = fields.Many2one(
        "res.partner",
        string="Paciente",
        required=True,
        domain=[("is_patient", "=", True)],
        # `show_vat` es de Odoo: muestra el documento junto al nombre en el
        # desplegable. Acá no es un adorno —es cómo la recepción distingue
        # homónimos, y en este sistema el documento puede repetirse a
        # propósito (doc 01), así que el nombre solo no alcanza.
        context={"default_is_patient": True, "show_vat": True},
    )
    insurer_id = fields.Many2one(
        "res.partner", string="Obra social", related="partner_id.insurer_id"
    )

    sale_order_template_id = fields.Many2one(
        "sale.order.template",
        string="Tipo de turno",
        required=True,
        domain=[("is_appointment", "=", True)],
        default=lambda self: self.env["sale.order.template"].search(
            [("is_appointment", "=", True)], limit=1),
        help="Define qué se le cobra al paciente. Una colonoscopía no es un "
        "ítem sino un conjunto: el estudio, los insumos y la anestesia.",
    )
    encounter_type_id = fields.Many2one(
        "emr.encounter.type",
        string="Historia clínica que genera",
        compute="_compute_encounter_type_id",
    )

    appointment_mode = fields.Selection(
        selection=lambda self: self.env["sale.order"]._fields[
            "appointment_mode"
        ].selection,
        string="Modalidad",
        required=True,
        default="scheduled",
    )
    appointment_priority = fields.Selection(
        [("0", "Alta"), ("1", "Media"), ("2", "Baja")],
        string="Prioridad",
        default="1",
    )
    note = fields.Text("Nota")

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Sobreturno sin hueco: la hora arranca en ahora, que es cuando el
        # paciente está en el mostrador pidiéndolo.
        if (
            res.get("appointment_mode") == "overbooked"
            and not res.get("slot_id")
            and "start" in fields_list
        ):
            res.setdefault("start", fields.Datetime.now())
        slot = self.env["emr.slot"].browse(res.get("slot_id") or 0)
        if slot:
            res.update(
                {
                    "practitioner_id": slot.practitioner_id.id,
                    "start": slot.start,
                    "location_id": slot.location_id.id or False,
                    "appointment_mode": (
                        "open" if slot.slot_type == "open" else "scheduled"
                    ),
                }
            )
        return res

    @api.depends("sale_order_template_id")
    def _compute_encounter_type_id(self):
        """Qué historia clínica va a abrir este turno.

        Sale del primer producto del tipo de turno que sea una práctica. Se
        muestra al asignar para que la regla deje de estar escondida.
        """
        for wiz in self:
            products = wiz.sale_order_template_id.sale_order_template_line_ids.product_id
            procedure = products.filtered(
                lambda p: p.is_medical_procedure and p.encounter_type_id
            )[:1]
            wiz.encounter_type_id = procedure.encounter_type_id

    @api.onchange("practitioner_id")
    def _onchange_practitioner_location(self):
        """Sin hueco no hay locación heredada, así que se propone la última.

        En sobreturno, demanda espontánea y guardia la locación es lo primero
        que se pierde, y es justo donde más ambigua es.
        """
        if self.slot_id or not self.practitioner_id:
            return
        last = self.env["sale.order"].search(
            [
                ("is_appointment", "=", True),
                ("practitioner_id", "=", self.practitioner_id.id),
                ("location_id", "!=", False),
            ],
            order="id desc",
            limit=1,
        )
        if last:
            self.location_id = last.location_id

    # ------------------------------------------------------------------
    # Alta
    # ------------------------------------------------------------------
    def _prepare_order_vals(self):
        self.ensure_one()
        # El turno es de la clínica, no del profesional: la agenda, el hueco y
        # el consultorio son de la institución, y un profesional que factura
        # por su cuenta usa un recurso que no es suyo. Por eso la compañía
        # sale del hueco —o de la locación, en las modalidades que no tienen
        # hueco— y no de `invoicing_company_id`, que gobierna la factura y el
        # cobro pero no el turno.
        company = (
            self.slot_id.company_id
            or self.location_id.company_id
            or self.env.company.root_id
        )
        pricelist = (
            self.partner_id.insurer_id.insurer_pricelist_id
            or self.partner_id.property_product_pricelist
        )
        vals = {
            "partner_id": self.partner_id.id,
            "company_id": company.id,
            "is_appointment": True,
            "practitioner_id": self.practitioner_id.id,
            "slot_id": self.slot_id.id or False,
            "location_id": self.location_id.id or False,
            "appointment_start": self.start,
            "appointment_mode": self.appointment_mode,
            "appointment_state": "booked",
            "appointment_priority": self.appointment_priority,
        }
        if pricelist:
            vals["pricelist_id"] = pricelist.id
        if self.note:
            vals["note"] = self.note
        return vals

    def action_book(self):
        self.ensure_one()
        if self.slot_id and not self.slot_id.available:
            raise UserError(_("Ese hueco ya tiene un turno asignado."))

        # El sobreturno no viene de la grilla, así que su hueco nace acá —con
        # el tope diario del profesional ya validado— y desde ese momento se ve
        # en la agenda como cualquier otro.
        if not self.slot_id and self.appointment_mode == "overbooked":
            self.slot_id = self.env["emr.slot"]._create_overbooking_slot(
                self.practitioner_id, self.start, location=self.location_id
            )

        order = self.env["sale.order"].create(self._prepare_order_vals())
        self._apply_template(order)

        if self.slot_id:
            # Solo el vínculo: el estado del hueco se calcula del turno.
            self.slot_id.write({"order_id": order.id})

        # Se encadena con el cobro: el caso normal es que el paciente esté
        # adelante y se asigne y se cobre de una. Si el turno es para más
        # adelante, se cancela el cobro y el turno queda agendado igual.
        return order.action_appointment_confirm()

    def _apply_template(self, order):
        self.ensure_one()
        return order._emr_apply_template(self.sale_order_template_id)
