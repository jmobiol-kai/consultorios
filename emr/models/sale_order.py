##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

APPOINTMENT_STATES = [
    ("waitlist", "En lista de espera"),
    ("booked", "Agendado"),
    ("confirmed", "Confirmado"),
    ("in_progress", "En atención"),
    ("done", "Atendido"),
    ("validated", "Validado"),
    ("no_show", "Ausente"),
    ("cancelled", "Cancelado"),
    ("void", "Anulado"),
]


class SaleOrder(models.Model):
    """El turno es una orden de venta.

    Es la unidad que se cobra, así que la orden ya trae líneas, precios,
    impuestos, factura y cobro. Lo que agregamos es la capa clínica: quién
    atiende, en qué hueco y en qué punto del recorrido está.

    El paciente es el partner_id de la orden. No hay un patient_id aparte.
    """

    _inherit = "sale.order"

    is_appointment = fields.Boolean("Es un turno", index=True, copy=False)

    practitioner_id = fields.Many2one(
        "res.partner",
        string="Profesional",
        index=True,
        domain=[("is_practitioner", "=", True)],
        context={"default_is_practitioner": True},
        tracking=False,
    )
    assistant_ids = fields.Many2many(
        "res.partner",
        "emr_order_assistant_rel",
        "order_id",
        "partner_id",
        string="Otros profesionales",
        domain=[("is_practitioner", "=", True)],
        context={"default_is_practitioner": True},
        help="Quienes acompañan la práctica: el anestesista de una endoscopía, "
        "por ejemplo.",
    )

    slot_id = fields.Many2one("emr.slot", string="Hueco", copy=False, index=True)
    location_id = fields.Many2one("emr.location", string="Locación", index=True)

    appointment_start = fields.Datetime("Inicio", index=True)
    appointment_mode = fields.Selection(
        [
            ("scheduled", "Turno programado"),
            ("overbooked", "Sobreturno"),
            ("open", "Franja variable"),
            ("waitlist", "Reserva"),
            ("walkin", "Demanda espontánea"),
            ("emergency", "Guardia"),
            ("ward_round", "Pase de sala"),
            ("triage", "Triage"),
            ("self", "Autogestión"),
        ],
        string="Modalidad",
        default="scheduled",
    )
    appointment_state = fields.Selection(
        APPOINTMENT_STATES, string="Estado del turno", default="booked", copy=False,
        index=True,
    )
    appointment_priority = fields.Selection(
        [("0", "Alta"), ("1", "Media"), ("2", "Baja")],
        string="Prioridad",
        default="1",
    )

    # Momento en que llegó y pagó. La cola de atención lo necesita para
    # ordenar y para mostrar cuánto hace que espera: no alcanza con el estado.
    confirmed_datetime = fields.Datetime("Llegada", readonly=True, copy=False)
    waiting_minutes = fields.Integer(
        "Espera (min)", compute="_compute_waiting_minutes"
    )

    encounter_id = fields.Many2one(
        "emr.encounter", string="Historia clínica", copy=False
    )

    # Reserva: se pide para un período, sin día ni hora.
    # Lo que se agrega sobre la marcha.
    #
    # El paciente entró por una consulta y le terminaron haciendo un banding.
    # Eso no es otro turno —no ocupa hueco, no se agenda, ya está adentro—
    # pero sí es otra práctica que hay que cobrar y que puede generar su
    # propia historia clínica. Va como una orden aparte colgada del turno:
    # meterla como línea de la original mezclaría dos atenciones en un mismo
    # comprobante y en una misma historia.
    parent_order_id = fields.Many2one(
        "sale.order", string="Turno original", index=True, copy=False,
        ondelete="set null",
    )
    additional_order_ids = fields.One2many(
        "sale.order", "parent_order_id", string="Prácticas agregadas",
    )
    additional_order_count = fields.Integer(
        compute="_compute_additional_order_count"
    )

    waitlist_period = fields.Date("Período deseado")

    log_ids = fields.One2many("emr.appointment.log", "order_id", string="Recorrido")

    @api.depends("additional_order_ids")
    def _compute_additional_order_count(self):
        for order in self:
            order.additional_order_count = len(order.additional_order_ids)

    def _emr_apply_template(self, template):
        """Carga las líneas de lo que se le va a cobrar.

        El tipo de turno es una plantilla de venta: trae el estudio y todo lo
        que lo acompaña, sin que la recepción tenga que armarlo. Vive acá y no
        en el asistente porque lo usan los dos: el que asigna el turno y el
        que le agrega una práctica.
        """
        self.ensure_one()
        self.sale_order_template_id = template
        self._onchange_sale_order_template_id()
        # La plantilla es la que dice si esto es un turno. Sin eso, la sección
        # del profesional no aparece y la orden es una venta cualquiera.
        if template.is_appointment:
            self.is_appointment = True
        return True

    def _emr_invoice_journal(self, company):
        """El diario de ventas con el que factura esa compañía.

        Se prefiere uno propio antes que uno heredado del padre: cuando el
        profesional tiene otro CUIT, emitir por el talonario de la clínica
        sería emitir a nombre de otra entidad legal. El heredado queda como
        alternativa para la sucursal del mismo CUIT, que sí comparte
        numeración.
        """
        Journal = self.env["account.journal"]
        propio = Journal.search(
            [("company_id", "=", company.id), ("type", "=", "sale")], limit=1
        )
        if propio:
            return propio
        return Journal.search(
            [*Journal._check_company_domain(company), ("type", "=", "sale")], limit=1
        )

    def _prepare_invoice(self):
        """La factura se emite en la compañía que declara el profesional.

        El turno vive en la clínica —la agenda es suya— pero el comprobante
        lo emite quien cobra: un profesional que factura por su cuenta lo
        emite con su CUIT y su talonario. Son dos compañías distintas en la
        misma cadena, y Odoo lo permite porque el plan de cuentas y los
        impuestos de la compañía madre se comparten hacia abajo
        (`check_company_domain_parent_of`), y el vínculo entre la línea de la
        factura y la del pedido no valida compañía.

        Lo que sí es de cada compañía y hay que rehacer al cruzar: el diario,
        la condición de pago y la posición fiscal. Si no se filtran, la
        factura nace con registros de la clínica y Odoo la rechaza por cruce.
        """
        vals = super()._prepare_invoice()
        if not self.is_appointment or not self.practitioner_id:
            return vals

        company = self.practitioner_id._emr_invoicing_company()
        if company == self.company_id:
            return vals

        journal = self._emr_invoice_journal(company)
        if not journal:
            raise UserError(
                _(
                    "%(company)s no tiene diario de ventas, así que no puede "
                    "emitir la factura del turno de %(practitioner)s. Se "
                    "configura en Contabilidad, con su punto de venta.",
                    company=company.display_name,
                    practitioner=self.practitioner_id.display_name,
                )
            )

        vals["company_id"] = company.id
        vals["journal_id"] = journal.id

        # Condición de pago y posición fiscal: se conservan solo si la
        # compañía que emite las puede usar; si no, la posición se resuelve
        # de nuevo en esa compañía y la condición se deja vacía.
        term = self.env["account.payment.term"].browse(
            vals.get("invoice_payment_term_id") or []
        )
        if term and not term.filtered_domain(term._check_company_domain(company)):
            vals["invoice_payment_term_id"] = False

        fpos = self.env["account.fiscal.position"].browse(
            vals.get("fiscal_position_id") or []
        )
        if fpos and not fpos.filtered_domain(fpos._check_company_domain(company)):
            vals["fiscal_position_id"] = (
                self.env["account.fiscal.position"]
                .with_company(company)
                ._get_fiscal_position(self.partner_invoice_id)
                .id
            )
        return vals

    def action_add_practice(self):
        """Abre el asistente para sumarle una práctica a este turno."""
        self.ensure_one()
        if not self.is_appointment:
            raise UserError(_("Esto no es un turno."))
        if self.parent_order_id:
            raise UserError(
                _("Esta ya es una práctica agregada. Sumá la nueva sobre el "
                  "turno original, %s.", self.parent_order_id.name)
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Agregar una práctica"),
            "res_model": "emr.appointment.addon",
            "view_mode": "form",
            "target": "new",
            "context": {"default_parent_order_id": self.id},
        }

    def action_view_additional_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Prácticas agregadas"),
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [("parent_order_id", "=", self.id)],
            "context": {"default_parent_order_id": self.id},
        }

    # ------------------------------------------------------------------
    # Cálculos
    # ------------------------------------------------------------------
    @api.depends("confirmed_datetime", "appointment_state")
    def _compute_waiting_minutes(self):
        now = fields.Datetime.now()
        for order in self:
            if order.appointment_state == "confirmed" and order.confirmed_datetime:
                delta = now - order.confirmed_datetime
                order.waiting_minutes = int(delta.total_seconds() // 60)
            else:
                order.waiting_minutes = 0

    # ------------------------------------------------------------------
    # Reglas
    # ------------------------------------------------------------------
    @api.constrains("is_appointment", "partner_id")
    def _check_patient(self):
        for order in self.filtered("is_appointment"):
            if not order.partner_id.is_patient:
                raise ValidationError(
                    _("El cliente de un turno tiene que estar marcado como paciente.")
                )

    @api.onchange("partner_id")
    def _onchange_partner_id_insurer_pricelist(self):
        """El arancel sale de la obra social, no del paciente.

        Es la única sutileza del precio y hay que dejarla explícita: el
        comportamiento por defecto de Odoo es tomar la lista del cliente.
        """
        if self.is_appointment and self.partner_id.insurer_id.insurer_pricelist_id:
            self.pricelist_id = self.partner_id.insurer_id.insurer_pricelist_id

    # ------------------------------------------------------------------
    # Recorrido del turno
    # ------------------------------------------------------------------
    def _log_appointment_state(self, state):
        self.env["emr.appointment.log"].create(
            [
                {
                    "order_id": order.id,
                    "appointment_state": state,
                    "user_id": self.env.user.id,
                }
                for order in self
            ]
        )

    def _set_appointment_state(self, state):
        self.write({"appointment_state": state})
        self._log_appointment_state(state)
        return True

    def action_appointment_confirm(self):
        """Llegó: abre el cobro.

        Confirmar el turno es cobrarlo, así que este botón no cambia el estado
        por su cuenta: abre el asistente que hace todo el acto —confirmar la
        orden, facturar, cobrar y conciliar— y es ese el que marca el turno.
        """
        self.ensure_one()
        if self.appointment_state not in ("booked", "waitlist"):
            raise UserError(
                _("Solo se puede confirmar un turno agendado o en lista de espera.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Cobrar turno"),
            "res_model": "emr.appointment.charge",
            "view_mode": "form",
            "target": "new",
            "context": {"default_order_id": self.id},
        }

    def _emr_mark_confirmed(self):
        """Deja el turno en sala. Lo llama el asistente de cobro."""
        self.write({"confirmed_datetime": fields.Datetime.now()})
        return self._set_appointment_state("confirmed")

    def action_appointment_start(self):
        """El profesional lo llama y empieza a atenderlo."""
        for order in self:
            if order.appointment_state != "confirmed":
                raise UserError(_("El paciente todavía no está en sala."))
        self._set_appointment_state("in_progress")
        return self._open_encounter()

    def action_appointment_no_show(self):
        """No vino nunca: nadie lo cobró y no hay comprobante que anular."""
        for order in self:
            if order.appointment_state != "booked":
                raise UserError(
                    _("Solo se puede marcar ausente un turno agendado y sin confirmar.")
                )
        return self._set_appointment_state("no_show")

    def _emr_no_show_from_attention(self):
        """Pagó, esperó, se lo llamó y no entró.

        Es un ausente distinto del anterior: acá **sí hay una factura
        emitida**, porque confirmar el turno es cobrarlo. Lo que se haga con
        ese cobro —retenerlo como cargo por ausencia o devolverlo con una nota
        de crédito— es una decisión del cliente y no se resuelve acá.
        """
        for order in self:
            if order.appointment_state not in ("confirmed", "in_progress"):
                raise UserError(
                    _("Este turno no está en atención ni esperando en sala.")
                )
        return self._set_appointment_state("no_show")

    def action_appointment_cancel(self):
        """Se cae el turno antes de cobrarlo: libera el hueco y anula la orden.

        Solo desde `booked` o `waitlist`, y no es una restricción caprichosa:
        mientras el turno no se cobró la orden es un presupuesto y cancelarla
        no cuesta nada. Una vez confirmado hay factura emitida —confirmar el
        turno es cobrarlo—, y eso se deshace con una nota de crédito, que es
        una decisión de quien administra y no un botón de la agenda.
        """
        for order in self:
            if order.appointment_state not in ("booked", "waitlist"):
                raise UserError(
                    _(
                        "%(name)s ya está %(state)s, así que no se cancela "
                        "desde acá. Si no se presentó, va como ausente; si ya "
                        "se le cobró, lo que corresponde es una nota de "
                        "crédito.",
                        name=order.name,
                        state=dict(APPOINTMENT_STATES).get(
                            order.appointment_state, order.appointment_state
                        ).lower(),
                    )
                )
        # El hueco no se toca: su estado se calcula del turno, así que pasa
        # a «Cancelado» solo y vuelve a ser asignable sin perder el rastro de
        # lo que pasó. Antes había que liberarlo a mano —`_free_slot`— y eso
        # borraba el vínculo con la orden.
        self._set_appointment_state("cancelled")
        return self.filtered(lambda o: o.state == "draft")._action_cancel()

    # ------------------------------------------------------------------
    # Historia clínica
    # ------------------------------------------------------------------
    def _encounter_type(self):
        """El tipo de historia lo decide la práctica, no el profesional.

        Se toma de la primera línea que sea una práctica médica.
        """
        self.ensure_one()
        line = self.order_line.filtered(
            lambda ln: ln.product_id.is_medical_procedure
            and ln.product_id.encounter_type_id
        )[:1]
        return line.product_id.encounter_type_id

    def _open_encounter(self):
        """Abre la historia clínica del turno, creándola si hace falta."""
        self.ensure_one()
        if not self.encounter_id:
            encounter_type = self._encounter_type()
            if not encounter_type:
                raise UserError(
                    _(
                        "La práctica de este turno no tiene definido un tipo de "
                        "historia clínica. Se configura en el producto."
                    )
                )
            child = self.env[encounter_type.model_name].create(
                {
                    "partner_id": self.partner_id.id,
                    "practitioner_id": self.practitioner_id.id,
                    "date": fields.Datetime.now(),
                    "order_id": self.id,
                    "location_id": self.location_id.id or False,
                    "company_id": self.company_id.id,
                    "encounter_type_id": encounter_type.id,
                }
            )
            self.encounter_id = child.encounter_id

        return {
            "type": "ir.actions.act_window",
            "res_model": self.encounter_id.res_model,
            "res_id": self.encounter_id.res_id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_encounter(self):
        return self._open_encounter()
