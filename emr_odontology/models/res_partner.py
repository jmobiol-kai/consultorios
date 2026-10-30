##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_open_odontogram(self):
        """Abre el odontograma del paciente y lo crea si no existe.

        Es uno por paciente. El botón de la ficha es la entrada: no hace
        falta pasar por una visita para ver cómo está la boca.
        """
        self.ensure_one()
        if not self.is_patient:
            raise UserError(_("Solo un paciente tiene odontograma."))
        chart = self.env["emr.odontogram"]._get_or_create(self)
        return {
            "type": "ir.actions.act_window",
            "name": _("Odontograma"),
            "res_model": "emr.odontogram",
            "res_id": chart.id,
            "view_mode": "form",
            "target": "current",
        }

    # ------------------------------------------------------------------
    # Atender ahora: paciente sin turno
    # ------------------------------------------------------------------
    @api.model
    def _emr_current_practitioner(self):
        """El profesional del usuario que está operando, si lo es."""
        partner = self.env.user.partner_id
        if partner.is_practitioner:
            return partner
        return self.search(
            [("is_practitioner", "=", True), ("user_ids", "in", self.env.uid)],
            limit=1,
        )

    def action_odontology_walkin(self):
        """Botón «Atender ahora» de la ficha y del odontograma.

        Si quien aprieta es un profesional, arranca la consulta de una. Si
        no, abre el asistente para elegir quién atiende.
        """
        self.ensure_one()
        if not self.is_patient:
            raise UserError(_("Solo se atiende a un paciente."))
        practitioner = self._emr_current_practitioner()
        if practitioner:
            return self._emr_odontology_walkin(practitioner)
        return {
            "type": "ir.actions.act_window",
            "name": _("Atender ahora"),
            "res_model": "emr.odontology.walkin",
            "view_mode": "form",
            "target": "new",
            "context": {"default_partner_id": self.id},
        }

    def _emr_odontology_walkin_template(self):
        template = self.env.ref(
            "emr_odontology.sale_order_template_consulta_odontologica",
            raise_if_not_found=False,
        )
        if template:
            return template
        tipo = self.env["emr.encounter.type"].search(
            [("model_name", "=", "emr.encounter.odontology")], limit=1
        )
        template = self.env["sale.order.template"].search(
            [
                ("is_appointment", "=", True),
                ("sale_order_template_line_ids.product_id.encounter_type_id",
                 "=", tipo.id),
            ],
            limit=1,
        ) if tipo else self.env["sale.order.template"]
        if not template:
            raise UserError(
                _("No hay un tipo de turno de consulta odontológica configurado.")
            )
        return template

    def _emr_odontology_walkin(self, practitioner):
        """Turno + consulta odontológica para el paciente que llegó sin turno.

        Reusa el camino de la demanda espontánea: el hueco sale de
        `emr.slot._create_demand_slot` si el profesional tiene franja de
        demanda abierta, y si no el turno queda sin hueco (demanda
        espontánea). La orden se arma con el mismo asistente de asignación,
        sin pasar por el cobro: el turno queda como presupuesto y pasa
        directo a «En atención». Lo que se marque en la visita se suma solo
        a ese presupuesto.

        Si ya hay una consulta odontológica abierta hoy para este paciente y
        este profesional, se abre esa en lugar de duplicar el turno.
        """
        self.ensure_one()
        practitioner.ensure_one()
        if not self.is_patient:
            raise UserError(_("Solo se atiende a un paciente."))
        SaleOrder = self.env["sale.order"]

        since = fields.Datetime.now() - timedelta(hours=12)
        open_order = SaleOrder.search(
            [
                ("is_appointment", "=", True),
                ("partner_id", "=", self.id),
                ("practitioner_id", "=", practitioner.id),
                ("appointment_state", "=", "in_progress"),
                ("encounter_id.state", "=", "draft"),
                ("encounter_id.res_model", "=", "emr.encounter.odontology"),
                ("appointment_start", ">=", since),
            ],
            order="id desc",
            limit=1,
        )
        if open_order:
            return open_order._open_encounter()

        slot = self.env["emr.slot"]
        try:
            with self.env.cr.savepoint():
                slot = self.env["emr.slot"]._create_demand_slot(practitioner)
        except UserError:
            # Sin franja de demanda abierta: se atiende igual, sin hueco.
            slot = self.env["emr.slot"]

        book = self.env["emr.appointment.book"].create(
            {
                "slot_id": slot.id or False,
                "practitioner_id": practitioner.id,
                "start": slot.start or fields.Datetime.now(),
                "location_id": slot.location_id.id or False,
                "partner_id": self.id,
                "sale_order_template_id": self._emr_odontology_walkin_template().id,
                "appointment_mode": "walkin",
            }
        )
        order = SaleOrder.create(book._prepare_order_vals())
        book._apply_template(order)
        if slot:
            slot.write({"order_id": order.id})
        order.write({"confirmed_datetime": fields.Datetime.now()})
        order._set_appointment_state("in_progress")
        return order._open_encounter()
