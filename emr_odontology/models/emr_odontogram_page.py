##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Fichas que recorre el paginador del odontograma de un paciente.

Es una vista SQL, no una tabla. Abrir la pantalla lee el odontograma y
las consultas; no inserta, no renumera y no borra filas. El id es
determinista: el odontograma es `id * 2` y cada consulta es `id * 2 + 1`.

La primera ficha apunta al odontograma de verdad. Guardar el mapa llama
a `write` y eso escribe `tooth_ids` en `emr.odontogram`. Atender ahora
sigue abriendo la atención de ese paciente.

Las fichas siguientes son de solo lectura. Muestran la fecha, el
profesional, lo que se marcó, el precio de cada práctica y el presupuesto.
No reescriben la visita ni el mapa, y no crean ni borran líneas del pedido.
"""
from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools import SQL

from .billing_rules import is_empty_draft
from .history_pager import (
    PAGE_VIEW_SQL,
    history_visit_ids,
    odontogram_pager_client_action,
    pager_page_ids,
)


class EmrOdontogramPage(models.Model):
    _name = "emr.odontogram.page"
    _description = "Ficha del odontograma"
    _auto = False
    _log_access = False
    _order = "sequence, id"

    partner_id = fields.Many2one("res.partner", string="Paciente", readonly=True)
    kind = fields.Selection(
        [
            ("chart", "Odontograma"),
            ("visit", "Consulta"),
        ],
        readonly=True,
    )
    sequence = fields.Integer(readonly=True)
    odontogram_id = fields.Many2one(
        "emr.odontogram",
        string="Odontograma",
        readonly=True,
    )
    odontology_id = fields.Many2one(
        "emr.encounter.odontology",
        string="Consulta",
        readonly=True,
    )
    # Escribible a propósito: el mapa de la primera ficha es el odontograma
    # del paciente, no una copia. El write de abajo lo vuelca.
    tooth_ids = fields.One2many(
        related="odontogram_id.tooth_ids",
        readonly=False,
        string="Piezas",
    )
    line_ids = fields.One2many(
        related="odontology_id.line_ids",
        readonly=True,
        string="Qué se hizo",
    )
    # La consulta delega estos campos en emr.encounter. El camino pasa por
    # encounter_id, que es la columna real, para no depender de la delegación.
    visit_date = fields.Datetime(
        related="odontology_id.encounter_id.date",
        string="Fecha",
    )
    practitioner_id = fields.Many2one(
        related="odontology_id.encounter_id.practitioner_id",
        string="Profesional",
    )
    visit_state = fields.Selection(
        related="odontology_id.encounter_id.state",
        string="Estado de la consulta",
    )
    order_id = fields.Many2one(
        related="odontology_id.encounter_id.order_id",
        string="Presupuesto",
    )
    currency_id = fields.Many2one(
        related="odontology_id.encounter_id.order_id.currency_id",
    )
    amount_total = fields.Monetary(
        related="odontology_id.encounter_id.order_id.amount_total",
        string="Total",
        currency_field="currency_id",
    )
    order_state = fields.Selection(
        related="odontology_id.encounter_id.order_id.state",
        string="Estado",
    )
    display_name = fields.Char(compute="_compute_display_name")

    def init(self):
        """Crea la vista. Si la versión anterior dejó una tabla, la saca.

        `drop_view_if_exists` no toca una tabla. Sin este drop, el upgrade
        de 19.0.1.18.0 no puede crear la vista porque el nombre está ocupado.
        """
        cr = self.env.cr
        tools.drop_view_if_exists(cr, self._table)
        cr.execute(
            """
            SELECT c.relkind
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = current_schema()
               AND c.relname = %s
            """,
            [self._table],
        )
        row = cr.fetchone()
        if row and row[0] == "r":
            cr.execute(SQL("DROP TABLE %s CASCADE", SQL.identifier(self._table)))
        cr.execute(
            SQL(
                "CREATE VIEW %s AS (%s)",
                SQL.identifier(self._table),
                SQL(PAGE_VIEW_SQL),
            )
        )

    @api.depends(
        "kind",
        "partner_id.name",
        "odontology_id.encounter_id.date",
        "odontology_id.encounter_id.practitioner_id.name",
    )
    def _compute_display_name(self):
        for page in self:
            if page.kind != "visit":
                page.display_name = _(
                    "Odontograma de %s", page.partner_id.name or ""
                )
                continue
            when = ""
            if page.visit_date:
                local = fields.Datetime.context_timestamp(page, page.visit_date)
                when = local.strftime("%d/%m/%Y %H:%M")
            who = page.practitioner_id.name or ""
            page.display_name = " · ".join(
                part for part in (when, who) if part
            ) or _("Consulta")

    def write(self, vals):
        """El mapa se guarda en el odontograma. La vista no se actualiza.

        Una consulta no se edita desde acá. Otro campo que no sea el mapa
        tampoco: no hay columnas que escribir.
        """
        if not self:
            return True
        self.check_access("write")
        extra = set(vals) - {"tooth_ids"}
        if extra:
            raise UserError(_("Esta ficha no se edita."))
        if "tooth_ids" not in vals:
            return True
        charts = self.filtered(lambda page: page.kind == "chart" and page.odontogram_id)
        if len(charts) != len(self):
            raise UserError(_("El mapa de una consulta no se modifica."))
        charts.odontogram_id.write({"tooth_ids": vals["tooth_ids"]})
        return True

    @api.model
    def action_open_for_partner(self, partner):
        """Arma los ids de la vista y los manda al cliente.

        No crea fichas. Si el paciente todavía no tiene odontograma y quien
        abre puede crearlo, se crea esa boca (igual que antes del paginador).
        Un usuario de solo lectura, con la boca ya creada, no escribe nada.
        """
        partner.ensure_one()
        Odontogram = self.env["emr.odontogram"]
        chart = Odontogram.search([("partner_id", "=", partner.id)], limit=1)
        if not chart:
            if not Odontogram.has_access("create"):
                raise UserError(_("Este paciente todavía no tiene odontograma."))
            chart = Odontogram._get_or_create(partner)
        visits = self.env["emr.encounter.odontology"].search(
            [("partner_id", "=", partner.id)]
        )
        rows = [
            (
                visit.id,
                visit.date,
                is_empty_draft(
                    visit.state,
                    bool(visit.order_id),
                    len(visit.line_ids),
                    visit.reason,
                    visit.notes,
                    len(visit.diagnosis_ids),
                ),
            )
            for visit in visits
        ]
        page_ids = pager_page_ids(chart.id, history_visit_ids(rows))
        view = self.env.ref("emr_odontology.emr_odontogram_page_view_form")
        return odontogram_pager_client_action(view.id, page_ids, _("Odontograma"))

    def action_odontology_walkin(self):
        """Atender ahora, igual que desde el odontograma.

        Abre la atención de este paciente. No cambia el presupuesto ni
        recorre el historial.
        """
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Elegí el paciente para atenderlo."))
        return self.partner_id.action_odontology_walkin()
