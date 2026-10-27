##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EmrAppointmentCharge(models.TransientModel):
    """El cobro del turno: llegó el paciente y pasa por el mostrador.

    Confirmar el turno es cobrarlo. Este asistente encadena todo lo que eso
    implica —confirmar la orden, facturar, cobrar y conciliar— para que en el
    mostrador sea un solo acto y no cuatro pantallas.

    Mientras el turno está agendado y sin pagar, la orden es un presupuesto:
    cancelarlo no cuesta nada. Recién acá se emite un comprobante.
    """

    _name = "emr.appointment.charge"
    _description = "Cobrar turno"

    order_id = fields.Many2one(
        "sale.order", string="Turno", required=True, readonly=True
    )
    partner_id = fields.Many2one(
        "res.partner", string="Paciente", related="order_id.partner_id"
    )
    practitioner_id = fields.Many2one(
        "res.partner", string="Profesional", related="order_id.practitioner_id"
    )
    insurer_id = fields.Many2one(
        "res.partner", string="Obra social", related="order_id.partner_id.insurer_id"
    )
    pricelist_id = fields.Many2one(
        "product.pricelist", string="Arancel", related="order_id.pricelist_id"
    )

    order_line_ids = fields.One2many(
        related="order_id.order_line", string="Qué se le cobra", readonly=True
    )
    currency_id = fields.Many2one(related="order_id.currency_id")
    amount_total = fields.Monetary(
        string="Total", related="order_id.amount_total"
    )

    allowed_journal_ids = fields.Many2many(
        "account.journal",
        string="Diarios disponibles",
        compute="_compute_allowed_journal_ids",
        help="Los propios de la compañía que emite el turno, más los de sus "
        "compañías padre que estén compartidos con ella.",
    )
    payment_line_ids = fields.One2many(
        "emr.appointment.charge.line", "charge_id", string="Cómo paga"
    )
    amount_paid = fields.Monetary("Suma de los pagos", compute="_compute_amounts")
    amount_diff = fields.Monetary("Diferencia", compute="_compute_amounts")

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------
    @api.model
    def _emr_charging_company(self, order):
        """La compañía por la que entra la plata de este turno.

        No es la del turno: el turno es de la clínica y la factura la emite
        quien declara el profesional (`_prepare_invoice`). El pago tiene que
        quedar en la misma compañía que la factura, o no hay forma de
        conciliarlos.
        """
        if order.practitioner_id:
            return order.practitioner_id._emr_invoicing_company()
        return order.company_id

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order = self.env["sale.order"].browse(res.get("order_id") or 0)
        if order and "payment_line_ids" in fields_list and order.amount_total:
            Journal = self.env["account.journal"]
            domain = [
                *Journal._check_company_domain(self._emr_charging_company(order))
            ]
            journal = Journal.search(
                domain + [("type", "=", "cash")], limit=1
            ) or Journal.search(
                domain + [("type", "=", "bank")], limit=1
            )
            # Se propone una sola línea por el total: el caso habitual es que
            # el paciente pague todo junto y de una sola forma.
            res["payment_line_ids"] = [
                (0, 0, {"journal_id": journal.id, "amount": order.amount_total})
            ]
        return res

    @api.depends("order_id.company_id", "order_id.practitioner_id")
    def _compute_allowed_journal_ids(self):
        """Con qué diarios se puede cobrar este turno.

        Se calcula en el asistente y no en la línea: adentro de un one2many
        sin guardar, el related de la línea todavía no resuelve y el dominio
        queda filtrando por compañía vacía.

        El criterio es el del propio modelo: `_check_company_domain` responde
        los diarios de la compañía que emite el turno más los de sus padres
        que estén compartidos con ella. Es el mismo chequeo que después valida
        el pago, así que lo que se ofrece acá es exactamente lo que se puede
        usar —y el profesional que factura por su cuenta cobra por la caja de
        la clínica sin que el asistente tenga que saber nada de sucursales.

        Antes era `child_of`, que mira para el otro lado: a una compañía hija
        sin diarios propios le devolvía la lista vacía.
        """
        Journal = self.env["account.journal"]
        for wiz in self:
            company = self._emr_charging_company(wiz.order_id)
            wiz.allowed_journal_ids = Journal.search(
                [
                    *Journal._check_company_domain(company),
                    ("type", "in", ("cash", "bank")),
                ]
            )

    @api.depends("payment_line_ids.amount", "amount_total")
    def _compute_amounts(self):
        for wiz in self:
            wiz.amount_paid = sum(wiz.payment_line_ids.mapped("amount"))
            wiz.amount_diff = wiz.amount_total - wiz.amount_paid

    # ------------------------------------------------------------------
    # El cobro
    # ------------------------------------------------------------------
    def action_manual(self):
        """Abre la orden para resolverla a mano.

        El camino automático cubre el caso normal: se cobra el total, en uno o
        varios medios, y sale la factura. Lo que no cubre es todo lo demás —un
        descuento, una seña, media obra social y media el paciente, un ajuste
        de la línea— y para eso está la orden, que ya sabe hacerlo.

        No toca el estado del turno. Quien elige el camino manual va a
        confirmar, facturar y cobrar desde la orden; adelantarle un paso le
        deja algo hecho a medias que después tiene que deshacer.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Turno"),
            "res_model": "sale.order",
            "res_id": self.order_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_charge(self):
        self.ensure_one()
        order = self.order_id

        if order.appointment_state not in ("booked", "waitlist"):
            raise UserError(_("Este turno ya fue confirmado."))

        # La atención sin cargo es un producto en cero: se confirma el turno y
        # no se emite nada. Un comprobante en cero no le sirve a nadie.
        if order.currency_id.is_zero(order.amount_total):
            order.action_confirm()
            return order._emr_mark_confirmed()

        if not self.payment_line_ids:
            raise UserError(_("Falta indicar cómo paga."))
        if not order.currency_id.is_zero(self.amount_diff):
            raise UserError(
                _(
                    "Los pagos suman %(pagado)s y el total es %(total)s. "
                    "Tiene que dar exacto.",
                    pagado=self.amount_paid,
                    total=self.amount_total,
                )
            )

        order.action_confirm()
        invoice = self._create_invoice(order)
        payments = self._create_payments(order, invoice)
        self._reconcile(invoice, payments)
        order._emr_mark_confirmed()

        return {
            "type": "ir.actions.act_window",
            "name": _("Factura"),
            "res_model": "account.move",
            "res_id": invoice.id,
            "view_mode": "form",
        }

    def _create_invoice(self, order):
        """Factura la orden y la valida.

        Si está `account_background_post`, se marca para posteo diferido: con
        facturación electrónica, validar llama a ARCA de forma sincrónica y no
        puede trabar el mostrador con el paciente adelante.
        """
        invoice = order._create_invoices()
        invoice.write(
            {
                "practitioner_id": order.practitioner_id.id,
                "assistant_ids": [(6, 0, order.assistant_ids.ids)],
            }
        )
        ctx = {}
        if "background_post" in self.env["account.move"]._fields:
            ctx["force_background_post"] = True
        invoice.with_context(**ctx).action_post()
        return invoice

    def _create_payments(self, order, invoice):
        """Un pago por cada forma de pago.

        El profesional viaja al pago: es lo que después permite liquidarle sin
        recorrer pago, factura, orden y turno por cada cobro.
        """
        Payment = self.env["account.payment"]
        payments = Payment.browse()
        for line in self.payment_line_ids:
            payments |= Payment.create(
                {
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "partner_id": order.partner_id.id,
                    "amount": line.amount,
                    "journal_id": line.journal_id.id,
                    "date": fields.Date.context_today(self),
                    # La de la factura, no la del turno: es la condición para
                    # poder conciliar uno contra la otra.
                    "company_id": invoice.company_id.id,
                    "practitioner_id": order.practitioner_id.id,
                    "memo": order.name,
                }
            )
        payments.action_post()
        return payments

    def _reconcile(self, invoice, payments):
        """Deja el cobro aplicado a la factura, no suelto en la cuenta."""
        lines = (invoice.line_ids | payments.move_id.line_ids).filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
            and not line.reconciled
        )
        if len(lines.mapped("account_id")) == 1:
            lines.reconcile()
        return True


class EmrAppointmentChargeLine(models.TransientModel):
    """Una forma de pago: con qué diario y cuánto.

    Son varias líneas porque un paciente puede pagar parte en efectivo y parte
    con tarjeta, y eso en el mostrador pasa seguido.
    """

    _name = "emr.appointment.charge.line"
    _description = "Forma de pago del turno"

    charge_id = fields.Many2one(
        "emr.appointment.charge", required=True, ondelete="cascade"
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario",
        required=True,
        domain="[('id', 'in', parent.allowed_journal_ids)]",
    )
    currency_id = fields.Many2one(related="charge_id.currency_id")
    amount = fields.Monetary("Monto", required=True)
