##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    """Paciente, profesional y obra social son roles sobre el partner.

    No son excluyentes a propósito: un profesional se atiende en su propia
    clínica, y ahí es paciente y profesional a la vez.
    """

    _inherit = "res.partner"

    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------
    is_patient = fields.Boolean("Es paciente", index=True)
    is_practitioner = fields.Boolean("Es profesional", index=True)
    is_insurer = fields.Boolean("Es obra social", index=True)

    # ------------------------------------------------------------------
    # Paciente
    # ------------------------------------------------------------------
    gender = fields.Selection(
        [("female", "Femenino"), ("male", "Masculino"), ("other", "Otro")],
        string="Género",
    )
    insurer_id = fields.Many2one(
        "res.partner",
        string="Obra social",
        domain=[("is_insurer", "=", True)],
        context={"default_is_insurer": True, "default_is_company": True},
        index=True,
    )
    insurance_member_number = fields.Char("Nº de afiliado")

    # ------------------------------------------------------------------
    # Obra social
    # ------------------------------------------------------------------
    insurer_pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Lista de precios",
        help="Arancel que se aplica a los turnos de los pacientes de esta obra "
        "social. Es la lista que toma la orden, por encima de la del paciente.",
    )

    # ------------------------------------------------------------------
    # Profesional
    # ------------------------------------------------------------------
    license_national = fields.Char("Matrícula nacional")
    license_provincial = fields.Char("Matrícula provincial")
    license_special = fields.Char("Matrícula especial")
    specialty_ids = fields.Many2many("emr.specialty", string="Especialidades")

    scheduling_method = fields.Selection(
        [("slots", "Entrega turnos"), ("walkin", "Por orden de llegada")],
        string="Método de turnos",
        help="Cómo entrega turnos este profesional. Vacío significa que no "
        "agenda: es el caso del médico que solo deriva o solicita estudios, "
        "que está en el padrón pero no atiende acá. Sin método no se le crea "
        "recurso ni agenda.",
    )
    resource_id = fields.Many2one("resource.resource", string="Recurso", copy=False)
    resource_calendar_id = fields.Many2one(
        "resource.calendar",
        string="Agenda",
        related="resource_id.calendar_id",
        readonly=False,
    )
    slot_generation_days = fields.Integer(
        "Días de agenda a generar",
        default=60,
        help="Cuánta agenda futura se materializa. Vacío usa el valor de la compañía.",
    )
    overbooking_daily_limit = fields.Integer(
        "Sobreturnos por día",
        help="Cuántos sobreturnos acepta este profesional por día. En cero no "
        "hay tope. No es una restricción del sistema sino un acuerdo con el "
        "profesional: el sobreturno se encaja sobre una agenda ya llena, y "
        "cuántos aguanta lo decide él.",
    )

    copay_percent = fields.Float(
        "% de coseguro",
        default=100.0,
        help="Porción de lo cobrado a su nombre que el profesional recibe al "
        "liquidar. 100 significa que se lleva todo; 90, que la clínica retiene "
        "el 10 %.",
    )
    invoicing_company_id = fields.Many2one(
        "res.company",
        string="Compañía que factura sus turnos",
        help="Gobierna el circuito de dinero del profesional: en qué compañía "
        "se emite la factura de sus turnos, dónde entra el cobro y qué "
        "compañía le liquida. El turno en sí queda en la clínica, que es de "
        "quien son la agenda y el consultorio. Vacío significa que factura la "
        "clínica.",
    )

    emr_slot_count = fields.Integer(
        "Huecos de agenda", compute="_compute_emr_slot_count"
    )

    # ------------------------------------------------------------------
    # Cálculos
    # ------------------------------------------------------------------
    def _compute_emr_slot_count(self):
        """Cuántos huecos tiene generados hacia adelante.

        Se agrupa en una sola consulta: este campo se lee en la ficha, pero
        también podría pedirse para varios profesionales a la vez.
        """
        counts = {}
        if self.ids:
            data = self.env["emr.slot"]._read_group(
                [
                    ("practitioner_id", "in", self.ids),
                    ("start", ">=", fields.Datetime.now()),
                ],
                groupby=["practitioner_id"],
                aggregates=["__count"],
            )
            counts = {partner.id: count for partner, count in data}
        for partner in self:
            partner.emr_slot_count = counts.get(partner.id, 0)

    def action_view_emr_slots(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Agenda de %s", self.name),
            "res_model": "emr.slot",
            "view_mode": "kanban,list,calendar",
            "domain": [("practitioner_id", "=", self.id)],
            "context": {"search_default_upcoming": 1},
        }

    def action_demand_appointment(self):
        """Atender al que acaba de llegar, sin turno previo.

        En demanda no hay grilla que mirar: se crea el hueco en el próximo
        momento libre y se pasa directo a asignarle el paciente.
        """
        self.ensure_one()
        slot = self.env["emr.slot"]._create_demand_slot(self)
        return slot.action_book()

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("is_insurer", "insurer_id")
    def _check_insurer_not_self(self):
        for partner in self:
            if partner.insurer_id and partner.insurer_id == partner:
                raise ValidationError(
                    _("Un partner no puede ser su propia obra social.")
                )

    @api.constrains("copay_percent")
    def _check_copay_percent(self):
        for partner in self:
            if partner.is_practitioner and not 0 <= partner.copay_percent <= 100:
                raise ValidationError(
                    _("El porcentaje de coseguro tiene que estar entre 0 y 100.")
                )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _emr_invoicing_company(self):
        """Compañía en la que se factura y se cobra lo que hace este profesional.

        No es la compañía del turno: el turno es de la clínica. Esta es la que
        emite el comprobante, recibe el pago y después le liquida.
        """
        self.ensure_one()
        return self.invoicing_company_id or self.env.company

    def action_print_history(self):
        """Imprime la historia clínica completa del paciente.

        Existe como método y no como una entrada más del menú Imprimir porque
        es la operación que uno busca estando en la ficha: ver todo lo que le
        pasó a esta persona. Un botón se encuentra; un desplegable no.
        """
        self.ensure_one()
        if not self.is_patient:
            raise UserError(_("%s no es un paciente.", self.display_name))
        return self.env.ref("emr.action_report_patient_history").report_action(self)

    def _emr_ensure_resource(self):
        """Crea el recurso del profesional si todavía no lo tiene.

        El recurso es lo que le da agenda: sin él no hay franjas ni huecos.

        Solo para quien efectivamente agenda, o sea quien tiene
        `scheduling_method`. El padrón de médicos que derivan es mucho más
        grande que el plantel: en CEMCO son 1.314 contra 46, y crearle un
        recurso a cada uno llena la tabla de recursos con gente que no
        atiende acá y nunca va a tener una franja.
        """
        Resource = self.env["resource.resource"]
        for partner in self:
            if (partner.is_practitioner and partner.scheduling_method
                    and not partner.resource_id):
                partner.resource_id = Resource.create(
                    {
                        "name": partner.name,
                        "company_id": partner.company_id.id or self.env.company.id,
                    }
                )
        return True

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners.filtered("is_practitioner")._emr_ensure_resource()
        return partners

    def write(self, vals):
        res = super().write(vals)
        # También al elegirle método: es el momento en que un profesional del
        # padrón pasa a atender acá y necesita agenda.
        if vals.get("is_practitioner") or vals.get("scheduling_method"):
            self.filtered("is_practitioner")._emr_ensure_resource()
        return res
