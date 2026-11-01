##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..wizards.walkin_default import (
    choose_walkin_practitioner,
    parse_stored_practitioner_id,
    walkin_practitioner_param_key,
)


class ResPartner(models.Model):
    _inherit = "res.partner"

    # El mapa es uno por paciente. La historia clínica lo muestra adentro;
    # no es la lista del menú. `copy=False`: duplicar un paciente no duplica
    # la boca, y el odontograma tampoco se deja copiar.
    odontogram_ids = fields.One2many(
        "emr.odontogram",
        "partner_id",
        string="Odontogramas",
        copy=False,
    )
    odontogram_id = fields.Many2one(
        "emr.odontogram",
        string="Odontograma",
        compute="_compute_odontogram_id",
    )
    odontogram_tooth_ids = fields.One2many(
        related="odontogram_id.tooth_ids",
        string="Piezas",
        readonly=True,
    )

    @api.depends("odontogram_ids")
    def _compute_odontogram_id(self):
        for partner in self:
            partner.odontogram_id = partner.odontogram_ids[:1]

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
    # Atención sin turno: la pantalla, y el presupuesto aparte
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

    @api.model
    def _emr_odontology_practitioner_domain(self):
        return [("is_practitioner", "=", True)]

    @api.model
    def _emr_odontology_remembered_practitioner_id(self):
        raw = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(walkin_practitioner_param_key(self.env.uid))
        )
        return parse_stored_practitioner_id(raw)

    @api.model
    def _emr_odontology_remember_practitioner(self, practitioner):
        """Guarda la elección de este usuario, no la de la clínica."""
        if not practitioner:
            return
        self.env["ir.config_parameter"].sudo().set_param(
            walkin_practitioner_param_key(self.env.uid),
            str(practitioner.id),
        )

    @api.model
    def _emr_odontology_default_practitioner(self):
        """Profesional de la atención, sin pedir una pantalla previa.

        Si quien opera es profesional, es ese. Si no, el único de la lista.
        Con varios, el último que este usuario confirmó con Nuevo, si sigue
        pudiendo elegirse. Si no hay ninguno, el campo queda vacío.
        """
        current = self._emr_current_practitioner()
        if current:
            return current
        Partner = self.env["res.partner"]
        domain = self._emr_odontology_practitioner_domain()
        available_count = Partner.search_count(domain)
        sole_id = False
        remembered_id = False
        remembered_allowed = False
        if available_count == 1:
            sole_id = Partner.search(domain, limit=1).id
        elif available_count > 1:
            remembered_id = self._emr_odontology_remembered_practitioner_id()
            if remembered_id:
                remembered_allowed = bool(
                    Partner.search_count(domain + [("id", "=", remembered_id)])
                )
        chosen = choose_walkin_practitioner(
            available_count,
            sole_id=sole_id,
            remembered_id=remembered_id,
            remembered_allowed=remembered_allowed,
        )
        return Partner.browse(chosen) if chosen else Partner.browse()

    def action_odontology_walkin(self):
        """Abre la atención de este paciente, sin crear un presupuesto.

        La historia clínica se ve en esa pantalla. El presupuesto lo crea
        Nuevo, al lado de Atendido.
        """
        self.ensure_one()
        if not self.is_patient:
            raise UserError(_("Solo se atiende a un paciente."))
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "emr_odontology.emr_odontology_walkin_action"
        )
        action["context"] = {
            "default_partner_id": self.id,
            "form_view_initial_mode": "edit",
        }
        action["target"] = "current"
        return action

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

    def _emr_odontology_prepare_walkin_order(self, practitioner):
        """Presupuesto de demanda espontánea, ya en atención, sin abrir visita.

        Es el mismo efecto que tenía «Atender ahora» sobre la orden: hueco de
        demanda si el profesional tiene franja abierta, y si no el turno queda
        sin hueco. No se cobra. Lo que después se marque en la consulta se
        suma solo a este presupuesto.
        """
        self.ensure_one()
        practitioner.ensure_one()
        if not self.is_patient:
            raise UserError(_("Solo se atiende a un paciente."))
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
        order = self.env["sale.order"].create(book._prepare_order_vals())
        book._apply_template(order)
        if slot:
            slot.write({"order_id": order.id})
        order.write({"confirmed_datetime": fields.Datetime.now()})
        order._set_appointment_state("in_progress")
        return order

    def _emr_odontology_attach_quotation(self, practitioner, encounter):
        """Crea el presupuesto y lo deja en esta visita.

        No abre otra historia: la pantalla ya es la atención. Si la visita
        ya tiene presupuesto, el que llama abre una visita nueva antes.
        """
        self.ensure_one()
        order = self._emr_odontology_prepare_walkin_order(practitioner)
        vals = {
            "order_id": order.id,
            "practitioner_id": practitioner.id,
        }
        if order.location_id:
            vals["location_id"] = order.location_id.id
        if order.company_id:
            vals["company_id"] = order.company_id.id
        encounter.write(vals)
        order.encounter_id = encounter.encounter_id
        view = self.env.ref("emr_odontology.emr_encounter_odontology_view_form")
        return {
            "type": "ir.actions.act_window",
            "name": _("Atención"),
            "res_model": "emr.encounter.odontology",
            "res_id": encounter.id,
            "view_mode": "form",
            "views": [(view.id, "form")],
            "target": "current",
        }
