##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""La receta: un flujo propio que se lista con las atenciones.

No es una atención. La toma un administrativo, la autoriza un médico y la
retira el paciente; nadie atiende a nadie en el medio. Tiene su modelo, su
módulo y sus reglas.

Y aun así **delega en emr.encounter**, porque la receta tiene que aparecer en
la historia clínica del paciente como un ítem más entre las atenciones. Eso no
la convierte en una: le da una fila en la lista unificada, que es justo lo que
se necesita. Los campos comunes —paciente, fecha, profesional, estado,
adjuntos— se leen y se escriben desde el padre.

El flujo entra en los estados que emr.encounter ya tiene, sin agregar ninguno:

    draft    el administrativo tomó el pedido    -> intake_uid
    closed   transitorio: autorizar encadena los dos pasos
    signed   el médico autorizó                  -> signed_by, practitioner_id

La entrega no es un estado. Que la receta se haya retirado no cambia el
registro: la receta firmada es la misma antes y después.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EmrPrescription(models.Model):
    _name = "emr.prescription"
    _description = "Receta"
    _inherit = "emr.encounter.mixin"
    _inherits = {"emr.encounter": "encounter_id"}
    _order = "id desc"

    # partner_id, date, practitioner_id, encounter_type_id, state,
    # attachment_ids, signed_by y signed_date vienen del padre por delegación.
    #
    # No hay campo para elegir el médico: practitioner_id se escribe al
    # autorizar, con el partner del usuario que autoriza. Quien firma y quien
    # figura como profesional son la misma persona por construcción, y no por
    # disciplina de quien carga.

    name = fields.Char(
        "Número", readonly=True, copy=False, index=True, default="/"
    )
    requested_date = fields.Date(
        "Fecha de requerimiento",
        help="Para cuándo la necesita el paciente. Es un dato que se pide en "
        "el mostrador, no la fecha en que se registra.",
    )
    intake_uid = fields.Many2one(
        "res.users",
        string="Tomada por",
        readonly=True,
        default=lambda self: self.env.user,
        help="El administrativo que registró el pedido.",
    )

    delivered_date = fields.Datetime("Entregada", readonly=True, copy=False)
    delivered_by = fields.Many2one(
        "res.users", string="Entregada por", readonly=True, copy=False
    )
    # El canal de entrega —retiro o envío digital— queda para cuando exista un
    # segundo canal. Hoy solo se retira, y una selección de un solo valor no
    # informa nada. Sumarla después es un campo, no una migración.

    line_ids = fields.One2many(
        "emr.prescription.line", "prescription_id", string="Renglones"
    )
    notes = fields.Text("Observaciones")

    # ------------------------------------------------------------------
    # Alta
    # ------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "encounter_type_id" in fields_list and not res.get("encounter_type_id"):
            res["encounter_type_id"] = self._default_encounter_type().id
        return res

    @api.model
    def _default_encounter_type(self):
        """El tipo se busca por modelo, no por xmlid.

        Así el módulo no depende de que su propio registro de datos siga
        llamándose igual, y sirve para cualquier hijo que quiera copiar esto.
        """
        return self.env["emr.encounter.type"].search(
            [("model_name", "=", self._name)], limit=1
        )

    @api.model_create_multi
    def create(self, vals_list):
        tipo = None
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("emr.prescription") or "/"
                )
            # También acá y no solo en default_get: la migración y cualquier
            # alta programática no pasan por el formulario, y el tipo es
            # obligatorio en el padre.
            if not vals.get("encounter_type_id"):
                if tipo is None:
                    tipo = self._default_encounter_type()
                vals["encounter_type_id"] = tipo.id
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # El flujo
    # ------------------------------------------------------------------
    def action_authorize(self):
        """El médico autoriza: es un solo acto para él, dos para el registro.

        `action_sign` exige que la atención esté cerrada, así que se encadenan
        los dos pasos. No hace falta tocar nada de emr: las dos son públicas y
        se respeta la secuencia.
        """
        partner = self.env.user.partner_id
        if not partner.is_practitioner:
            raise UserError(
                _(
                    "Solo un profesional puede autorizar una receta, y el "
                    "contacto de tu usuario (%s) no está marcado como "
                    "profesional.",
                    partner.display_name,
                )
            )
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Esta receta ya está autorizada."))
            if not rec.line_ids:
                raise UserError(
                    _("Una receta sin renglones no se puede autorizar.")
                )
            rec.practitioner_id = partner
        self.action_close()
        return self.action_sign()

    def action_deliver(self):
        """Registra la entrega, que ocurre después de la firma.

        Va con `emr_allow_signed_edit` a propósito. El mixin bloquea toda
        escritura sobre el hijo de una atención firmada, y hace bien: los
        campos clínicos no se tocan más. Pero la entrega no es información
        clínica — es un hecho administrativo posterior, y no cambia lo que la
        receta dice.
        """
        for rec in self:
            if rec.state != "signed":
                raise UserError(
                    _("Una receta que no está autorizada no se puede entregar.")
                )
            if rec.delivered_date:
                raise UserError(_("Esta receta ya fue entregada."))
        return self.with_context(emr_allow_signed_edit=True).write(
            {
                "delivered_date": fields.Datetime.now(),
                "delivered_by": self.env.user.id,
            }
        )


class EmrPrescriptionLine(models.Model):
    """Un renglón de la receta.

    `name` es lo que se escribió, y es obligatorio; `medication_id` es
    opcional y apunta al vademécum cuando hay correspondencia.

    Ese orden —el texto primero, el catálogo después— no es comodidad. En el
    sistema que se reemplaza el renglón era una referencia a un vocabulario
    con autocreación de términos: cada vez que alguien escribía algo que no
    existía, se creaba la entrada. El resultado fueron 21.490 "medicamentos"
    que no son un catálogo sino el historial de lo que se tipeó, con apenas
    160 nombres en común con el vademécum real de 8.985. El dato bueno de esas
    105.918 filas es el texto; la referencia se reconstruye donde se puede.
    """

    _name = "emr.prescription.line"
    _description = "Renglón de receta"
    _order = "prescription_id, sequence, id"

    prescription_id = fields.Many2one(
        "emr.prescription", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(default=10)
    name = fields.Char("Lo prescripto", required=True)
    medication_id = fields.Many2one("emr.medication", string="Medicamento")
    unit_text = fields.Char(
        "Presentación",
        size=20,
        help="Texto libre. En el origen hay 934 valores distintos en 20 "
        "caracteres: no es un catálogo de unidades.",
    )
    indication = fields.Char("Indicación", size=200)

    display_name = fields.Char(compute="_compute_display_name")

    @api.depends("name", "unit_text", "indication")
    def _compute_display_name(self):
        """Se arma a mano porque así se lee en el resumen de la historia.

        El panel del paciente vuelca los one2many uniendo los display_name, y
        "Ibuprofeno 400" solo no dice lo que hay que saber.
        """
        for line in self:
            partes = [p for p in (line.name, line.unit_text, line.indication) if p]
            line.display_name = " · ".join(partes)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_not_signed()
        return records

    def write(self, vals):
        """La guarda del padre no alcanza, igual que en el mixin.

        Escribir el renglón directamente no pasa por emr.prescription, así que
        sin esto una receta firmada se podría seguir editando por donde
        importa: lo prescripto.
        """
        self._check_not_signed()
        return super().write(vals)

    def unlink(self):
        self._check_not_signed()
        return super().unlink()

    def _check_not_signed(self):
        if self.env.context.get("emr_allow_signed_edit"):
            return
        if any(line.prescription_id.state != "draft" for line in self):
            raise UserError(
                _(
                    "Esta receta ya está autorizada y sus renglones no se "
                    "pueden modificar."
                )
            )
