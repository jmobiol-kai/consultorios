##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EmrSettlement(models.TransientModel):
    """Rendirle a un profesional lo que se cobró a su nombre.

    Se juntan los cobros en efectivo que todavía no se le rindieron, se aplica
    su porcentaje de coseguro y se emite un pago por esa parte. Los cobros
    quedan marcados como rendidos, que es lo único que impide pagarle dos
    veces lo mismo.

    Solo cuenta lo cobrado en efectivo: lo que entró por banco o tarjeta no
    está en la caja, y rendir plata que no se tiene es otro problema.
    """

    _name = "emr.settlement"
    _description = "Rendir a un profesional"

    practitioner_id = fields.Many2one(
        "res.partner",
        string="Profesional",
        required=True,
        domain=[("is_practitioner", "=", True)],
        context={"default_is_practitioner": True},
    )
    date_from = fields.Date("Desde", required=True)
    date_to = fields.Date(
        "Hasta", required=True, default=fields.Date.context_today
    )

    journal_id = fields.Many2one(
        "account.journal",
        string="Se paga desde",
        required=True,
        domain="[('type', '=', 'cash'), ('id', 'in', allowed_journal_ids)]",
        help="La caja de la que sale el dinero que se le entrega.",
    )
    allowed_journal_ids = fields.Many2many(
        "account.journal", compute="_compute_allowed_journal_ids"
    )
    date = fields.Date("Fecha del pago", required=True,
                       default=fields.Date.context_today)

    payment_ids = fields.Many2many(
        "account.payment",
        string="Cobros a rendir",
        compute="_compute_payment_ids",
        readonly=True,
    )
    payment_count = fields.Integer(compute="_compute_payment_ids")
    currency_id = fields.Many2one(
        "res.currency", compute="_compute_payment_ids"
    )
    amount_collected = fields.Monetary(
        "Cobrado a su nombre", compute="_compute_payment_ids"
    )
    copay_percent = fields.Float(
        "% que le corresponde", related="practitioner_id.copay_percent"
    )
    amount_to_settle = fields.Monetary(
        "A rendir", compute="_compute_payment_ids"
    )
    amount_retained = fields.Monetary(
        "Queda en la clínica", compute="_compute_payment_ids"
    )

    # ------------------------------------------------------------------
    # Cálculos
    # ------------------------------------------------------------------
    @api.depends_context("company")
    def _compute_allowed_journal_ids(self):
        for wiz in self:
            wiz.allowed_journal_ids = self.env["account.journal"].search(
                [("type", "=", "cash")]
            )

    @api.depends("practitioner_id", "date_from", "date_to")
    def _compute_payment_ids(self):
        for wiz in self:
            pagos = wiz._pending_payments()
            wiz.payment_ids = pagos
            wiz.payment_count = len(pagos)
            wiz.currency_id = (
                pagos[:1].currency_id or wiz.practitioner_id.currency_id
                or self.env.company.currency_id
            )
            cobrado = sum(pagos.mapped("amount"))
            wiz.amount_collected = cobrado
            wiz.amount_to_settle = cobrado * (wiz.copay_percent or 0.0) / 100.0
            wiz.amount_retained = cobrado - wiz.amount_to_settle

    def _pending_payments(self):
        """Lo cobrado a su nombre, en efectivo, que todavía no se le rindió."""
        self.ensure_one()
        if not (self.practitioner_id and self.date_from and self.date_to):
            return self.env["account.payment"]
        return self.env["account.payment"].search(
            [
                ("practitioner_id", "=", self.practitioner_id.id),
                ("payment_type", "=", "inbound"),
                ("state", "=", "paid"),
                ("emr_settled", "=", False),
                # Solo efectivo: lo que entró por banco o tarjeta no está en
                # la caja para entregarlo.
                ("journal_id.type", "=", "cash"),
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
            ],
            order="date, id",
        )

    # ------------------------------------------------------------------
    # La rendición
    # ------------------------------------------------------------------
    def action_settle(self):
        self.ensure_one()
        pagos = self._pending_payments()
        if not pagos:
            raise UserError(
                _("No hay cobros en efectivo pendientes de rendir en ese período.")
            )
        if self.currency_id.is_zero(self.amount_to_settle):
            raise UserError(
                _(
                    "El porcentaje de %s es 0, así que no hay nada que "
                    "rendirle.",
                    self.practitioner_id.display_name,
                )
            )

        pago = self.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.practitioner_id.id,
                "amount": self.amount_to_settle,
                "journal_id": self.journal_id.id,
                "date": self.date,
                "practitioner_id": self.practitioner_id.id,
                "memo": _(
                    "Rendición %(desde)s a %(hasta)s",
                    desde=self.date_from,
                    hasta=self.date_to,
                ),
            }
        )
        pago.action_post()

        # Marcar los cobros es lo que cierra el circuito: sin esto, la próxima
        # rendición del mismo período vuelve a pagarlos.
        pagos.write({"emr_settled": True, "emr_settlement_id": pago.id})

        return {
            "type": "ir.actions.act_window",
            "name": _("Rendición"),
            "res_model": "account.payment",
            "res_id": pago.id,
            "view_mode": "form",
        }
