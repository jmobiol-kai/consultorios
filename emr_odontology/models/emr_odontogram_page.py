##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Fichas que recorre el paginador del odontograma de un paciente.

El paginador de un formulario de Odoo camina `res_ids` de un solo modelo.
Por eso la boca actual y cada consulta son filas de este modelo, no del
odontograma y de la visita por separado.

La primera ficha apunta al odontograma de verdad. Las piezas se editan
ahí, igual que antes: `tooth_ids` escribe en `emr.odontogram`. Atender
ahora sigue abriendo la atención de ese paciente.

Las fichas siguientes son de solo lectura. Muestran la fecha, el
profesional, lo que se marcó, el precio de cada práctica y el presupuesto.
No reescriben la visita ni el mapa, y no crean ni borran líneas del pedido.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .billing_rules import is_empty_draft
from .history_pager import history_visit_ids, odontogram_pager_action


class EmrOdontogramPage(models.Model):
    _name = "emr.odontogram.page"
    _description = "Ficha del odontograma"
    _order = "sequence, id"

    partner_id = fields.Many2one(
        "res.partner",
        string="Paciente",
        required=True,
        index=True,
        ondelete="cascade",
    )
    kind = fields.Selection(
        [
            ("chart", "Odontograma"),
            ("visit", "Consulta"),
        ],
        required=True,
        index=True,
    )
    sequence = fields.Integer(default=0, index=True)
    odontogram_id = fields.Many2one(
        "emr.odontogram",
        string="Odontograma",
        ondelete="cascade",
        index=True,
    )
    odontology_id = fields.Many2one(
        "emr.encounter.odontology",
        string="Consulta",
        ondelete="cascade",
        index=True,
    )
    # Escribible a propósito: el mapa de la primera ficha es el odontograma
    # del paciente, no una copia.
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

    _odontology_page_uniq = models.Constraint(
        "UNIQUE (odontology_id)",
        "Esa consulta ya está en el historial.",
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

    @api.model
    def _sync_for_partner(self, partner):
        """Arma las fichas de este paciente y las devuelve en orden del paginador.

        La primera es el odontograma. Después, las consultas que no son un
        borrador vacío, de la más nueva a la más vieja. Lo que el usuario no
        puede leer no entra: vale la misma regla que en las consultas.
        """
        partner.ensure_one()
        chart = self.env["emr.odontogram"]._get_or_create(partner)
        chart_pages = self.search(
            [("partner_id", "=", partner.id), ("kind", "=", "chart")],
            order="id",
        )
        chart_page = chart_pages[:1]
        if chart_pages[1:]:
            chart_pages[1:].unlink()
        if not chart_page:
            chart_page = self.create({
                "partner_id": partner.id,
                "kind": "chart",
                "odontogram_id": chart.id,
                "sequence": 0,
            })
        elif chart_page.odontogram_id != chart or chart_page.sequence:
            chart_page.write({"odontogram_id": chart.id, "sequence": 0})

        visits = self.env["emr.encounter.odontology"].search(
            [("partner_id", "=", partner.id)],
            order="date desc, id desc",
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
        ordered_visit_ids = history_visit_ids(rows)
        existing = self.search([
            ("partner_id", "=", partner.id),
            ("kind", "=", "visit"),
        ])
        by_visit = {page.odontology_id.id: page for page in existing}
        page_ids = []
        for sequence, visit_id in enumerate(ordered_visit_ids, start=1):
            page = by_visit.get(visit_id)
            if not page:
                page = self.create({
                    "partner_id": partner.id,
                    "kind": "visit",
                    "odontology_id": visit_id,
                    "sequence": sequence,
                })
            elif page.sequence != sequence:
                page.sequence = sequence
            page_ids.append(page.id)
        stale = existing.filtered(lambda page: page.id not in page_ids)
        if stale:
            stale.unlink()
        return self.browse([chart_page.id, *page_ids])

    def action_open_for_partner(self, partner):
        """Abre el odontograma y deja el paginador sobre estas fichas."""
        pages = self._sync_for_partner(partner)
        view = self.env.ref("emr_odontology.emr_odontogram_page_view_form")
        return odontogram_pager_action(view.id, pages.ids, _("Odontograma"))

    def action_odontology_walkin(self):
        """Atender ahora, igual que desde el odontograma.

        Abre la atención de este paciente. No cambia el presupuesto ni
        recorre el historial.
        """
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Elegí el paciente para atenderlo."))
        return self.partner_id.action_odontology_walkin()
