##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import markupsafe

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class EmrEncounter(models.Model):
    """El registro clínico: una fila por atención, sea del tipo que sea.

    Cada tipo de historia clínica es un modelo propio que se apoya en este por
    delegación (_inherits). Gracias a eso, esta tabla ya es la lista unificada:
    ver todas las atenciones de un paciente es filtrar acá, sin construir
    ninguna vista que una modelos.

    No lleva mail.thread a propósito. Una conversación informal dentro de un
    registro clínico vuelve ambiguo qué es parte de la historia y qué es un
    comentario al pasar. Para sumar información está el agregado, que es
    explícito y firmado.
    """

    _name = "emr.encounter"
    _description = "Atención"
    _order = "date desc, id desc"

    partner_id = fields.Many2one(
        "res.partner",
        string="Paciente",
        required=True,
        index=True,
        domain=[("is_patient", "=", True)],
        context={"default_is_patient": True, "show_vat": True},
        ondelete="restrict",
    )
    practitioner_id = fields.Many2one(
        "res.partner",
        string="Profesional",
        index=True,
        domain=[("is_practitioner", "=", True)],
        context={"default_is_practitioner": True},
        ondelete="restrict",
        help="Quién atendió. No es obligatorio mientras la atención está en "
        "elaboración: hay circuitos que arrancan en recepción, antes de que "
        "se sepa qué profesional interviene. Al cerrar o firmar sí lo es — "
        "lo exige _check_practitioner.",
    )
    date = fields.Datetime(
        "Fecha de atención", required=True, index=True, default=fields.Datetime.now
    )

    order_id = fields.Many2one(
        "sale.order",
        string="Turno",
        index=True,
        help="Una atención suele venir de un turno, pero no siempre: la "
        "atención sin turno existe y es frecuente.",
    )
    location_id = fields.Many2one("emr.location", string="Locación")
    company_id = fields.Many2one(
        "res.company", required=True, index=True, default=lambda self: self.env.company
    )

    encounter_type_id = fields.Many2one(
        "emr.encounter.type", string="Tipo", required=True, index=True
    )
    res_model = fields.Char(
        related="encounter_type_id.model_name", store=True, string="Modelo"
    )
    res_id = fields.Integer("Id del registro", index=True, readonly=True)

    diagnosis_ids = fields.Many2many("emr.diagnosis", string="Diagnósticos")

    state = fields.Selection(
        [
            ("draft", "En elaboración"),
            ("closed", "Cerrada"),
            ("signed", "Firmada"),
        ],
        default="draft",
        required=True,
        index=True,
    )
    closed_by = fields.Many2one("res.users", string="Cerrada por", readonly=True)
    closed_date = fields.Datetime("Fecha de cierre", readonly=True)
    signed_by = fields.Many2one("res.users", string="Firmada por", readonly=True)
    signed_date = fields.Datetime("Fecha de firma", readonly=True)

    addendum_ids = fields.One2many(
        "emr.encounter.addendum", "encounter_id", string="Agregados"
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "emr_encounter_attachment_rel",
        "encounter_id",
        "attachment_id",
        string="Imágenes y estudios",
    )

    active = fields.Boolean(
        default=True,
        help="Una atención descartada se archiva, no se borra: en un registro "
        "clínico conviene que quede el rastro de que alguien abrió algo y lo "
        "dio de baja.",
    )

    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("partner_id", "encounter_type_id", "date")
    def _compute_display_name(self):
        for enc in self:
            enc.display_name = "%s - %s" % (
                enc.encounter_type_id.name or "",
                enc.partner_id.name or "",
            )

    # ------------------------------------------------------------------
    # Apertura del tipo concreto
    # ------------------------------------------------------------------
    def action_open(self):
        """Abre el formulario del tipo que corresponda.

        La lista muestra este modelo; el formulario que hay que abrir es el del
        hijo, que es donde están los campos clínicos.
        """
        self.ensure_one()
        if not self.res_model or not self.res_id:
            raise UserError(_("Esta atención no tiene su registro de detalle."))
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "view_mode": "form",
            "target": "current",
        }

    # ------------------------------------------------------------------
    # Cierre y firma
    # ------------------------------------------------------------------
    @api.constrains("practitioner_id", "state")
    def _check_practitioner(self):
        """El profesional es obligatorio, pero no desde el primer instante.

        `practitioner_id` no lleva `required=True` a propósito. Una atención
        en elaboración puede no tener profesional todavía: el pedido de una
        receta lo toma recepción y el médico entra después, cuando autoriza.
        Con el campo obligatorio en la creación, ese circuito no tiene forma
        de guardar el pedido y termina inventando un profesional para poder
        hacerlo — que es exactamente lo que pasó en el sistema que se
        reemplaza, donde el módulo de recetas creaba al instalarse un usuario
        falso con rol médico y le atribuía 34.688 recetas.

        La garantía se mantiene donde importa: nada se cierra ni se firma sin
        profesional. Un registro clínico terminado siempre tiene un
        responsable.
        """
        for enc in self:
            if enc.state != "draft" and not enc.practitioner_id:
                raise ValidationError(
                    _("No se puede cerrar ni firmar una atención sin profesional.")
                )

    def action_close(self):
        """Termina la atención. Es lo que cierra el turno.

        El turno no se cierra a mano: lo cierra el cierre de la historia
        clínica, que es la única señal confiable de que la atención terminó.
        """
        for enc in self:
            if enc.state != "draft":
                raise UserError(_("Esta atención ya está cerrada."))
        self.write(
            {
                "state": "closed",
                "closed_by": self.env.user.id,
                "closed_date": fields.Datetime.now(),
            }
        )
        orders = self.mapped("order_id").filtered(
            lambda o: o.appointment_state == "in_progress"
        )
        orders._set_appointment_state("done")
        return True

    def action_sign(self):
        """Firma la historia y la vuelve inmutable.

        Es un acto aparte del cierre: puede ocurrir enseguida, al final del día
        o cuando alguien revisa.
        """
        for enc in self:
            if enc.state != "closed":
                raise UserError(
                    _("Solo se puede firmar una atención cerrada.")
                )
        return self.write(
            {
                "state": "signed",
                "signed_by": self.env.user.id,
                "signed_date": fields.Datetime.now(),
            }
        )

    @api.model
    def get_patient_history(self, partner_id, exclude_id=None, limit=20):
        """Las atenciones anteriores de un paciente, listas para dibujar.

        Devuelve el resumen ya renderizado con la plantilla de cada tipo, más
        lo que el componente necesita para actuar sobre cada una: a qué modelo
        y a qué id tiene que ir para abrirla.
        """
        dominio = [("partner_id", "=", partner_id)]
        if exclude_id:
            dominio.append(("id", "!=", exclude_id))
        encuentros = self.search(dominio, order="date desc, id desc", limit=limit)

        salida = []
        for enc in encuentros:
            plantilla = (
                enc.encounter_type_id.summary_template
                or "emr.encounter_summary_generic"
            )
            detalle = self.env[enc.res_model].browse(enc.res_id) if enc.res_id else None
            try:
                html = self.env["ir.qweb"]._render(
                    plantilla, self._emr_summary_context(enc, detalle)
                )
            except ValueError:
                # Un tipo puede declarar una plantilla que todavía no existe.
                # Que falte un resumen no puede dejar sin historia a los demás.
                html = self.env["ir.qweb"]._render(
                    "emr.encounter_summary_generic",
                    self._emr_summary_context(enc, detalle),
                )
            salida.append(
                {
                    "id": enc.id,
                    "res_model": enc.res_model,
                    "res_id": enc.res_id,
                    "state": enc.state,
                    "html": html,
                }
            )
        return salida

    def action_print(self):
        """El informe en PDF de esta atención, sea del tipo que sea.

        El informe vive en el módulo del tipo —la colonoscopía trae el suyo— así
        que acá no se puede nombrar uno fijo: se busca el que está declarado
        para el modelo del hijo, que es el mismo que Odoo ofrece en el menú
        Imprimir de ese formulario (`binding_model_id`).

        Si un tipo llegara a declarar dos informes, gana el primero y hay que
        decidirlo explícitamente: el lugar seria un campo en
        `emr.encounter.type`, al lado de `report_template`.
        """
        self.ensure_one()
        if not (self.res_model and self.res_id):
            raise UserError(
                _("Esta atención no tiene registro del que sacar el informe.")
            )
        report = self.env["ir.actions.report"].search(
            [("model", "=", self.res_model), ("report_type", "=", "qweb-pdf")],
            order="id",
            limit=1,
        )
        if not report:
            raise UserError(
                _(
                    "%s no tiene informe definido. Lo trae el módulo del tipo "
                    "de historia clínica.",
                    self.encounter_type_id.display_name,
                )
            )
        return report.report_action(self.env[self.res_model].browse(self.res_id))

    def _emr_summary_context(self, encuentro, detalle):
        """Lo que ve la plantilla de resumen.

        `campos` lo arma el hijo, que es el único que sabe cuáles son sus
        campos clínicos.
        """
        return {
            "encounter": encuentro,
            "detail": detalle,
            "campos": detalle._emr_summary_values() if detalle else [],
        }

    def action_no_show(self):
        return self.mapped("encounter_id").action_no_show()

    def action_wait(self):
        return self.mapped("encounter_id").action_wait()

    def action_retype(self):
        return self.mapped("encounter_id").action_retype()

    # ------------------------------------------------------------------
    # Inmutabilidad
    # ------------------------------------------------------------------
    def write(self, vals):
        """Una historia firmada no se modifica: se le agrega.

        Se dejan pasar solo los campos del propio acto de firma y los
        agregados, que son la vía prevista para sumar información.
        """
        allowed = {
            "state",
            "signed_by",
            "signed_date",
            "addendum_ids",
            "attachment_ids",
            "res_id",
            "active",
            "order_id",
        }
        if not self.env.context.get("emr_allow_signed_edit"):
            signed = self.filtered(lambda e: e.state == "signed")
            if signed and set(vals) - allowed:
                raise UserError(
                    _(
                        "Esta historia clínica está firmada y no se puede "
                        "modificar. Para sumar información, agregá un "
                        "agregado."
                    )
                )
        return super().write(vals)

    def unlink(self):
        if self.filtered(lambda e: e.state != "draft"):
            raise UserError(
                _("No se puede borrar una historia clínica cerrada o firmada.")
            )
        return super().unlink()


class EmrEncounterMixin(models.AbstractModel):
    """Lo que comparte todo tipo de historia clínica.

    Los modelos concretos heredan de acá y delegan en emr.encounter:

        class EmrEncounterConsultation(models.Model):
            _name = "emr.encounter.consultation"
            _inherit = "emr.encounter.mixin"
            _inherits = {"emr.encounter": "encounter_id"}
    """

    _name = "emr.encounter.mixin"
    _description = "Base de historia clínica"

    encounter_id = fields.Many2one(
        "emr.encounter", required=True, ondelete="cascade", index=True, auto_join=True
    )

    def _emr_summary_values(self):
        """Los campos propios de este tipo que tienen algo cargado.

        Se recorren en vez de listarlos a mano en cada plantilla. Escribir la
        lista en el QWeb garantiza que tarde o temprano quede desactualizada y
        que un dato cargado no se vea, que en una historia clínica es el peor
        error posible: el que mira cree que no hay nada.

        Solo los propios. Los comunes —paciente, profesional, fecha,
        diagnósticos— ya están en el encabezado, y repetirlos es ruido.
        """
        self.ensure_one()
        MAGICOS = {"id", "display_name", "create_uid", "create_date",
                   "write_uid", "write_date", "encounter_id"}
        etiquetas = self.fields_get()
        salida = []
        for nombre, campo in self._fields.items():
            if campo.inherited or nombre in MAGICOS or not campo.store:
                continue
            texto = self._emr_format_value(campo, self[nombre])
            if texto is None:
                continue
            salida.append({
                "name": nombre,
                "label": etiquetas.get(nombre, {}).get("string") or nombre,
                "value": texto,
                # Los relatos van en su propio renglón; lo corto entra al lado
                # de la etiqueta.
                "long": campo.type in ("text", "html") or len(str(texto)) > 60,
            })
        return salida

    def _emr_format_value(self, campo, valor):
        """El valor como texto, o None si no hay nada que mostrar."""
        if campo.type == "boolean":
            # Los booleanos se muestran siempre: en una colonoscopía,
            # "muestra enviada: no" es un dato, no un campo vacío.
            return _("Sí") if valor else _("No")
        if not valor:
            return None
        if campo.type == "many2one":
            return valor.display_name
        if campo.type in ("one2many", "many2many"):
            return ", ".join(valor.mapped("display_name"))
        if campo.type == "selection":
            return dict(campo._description_selection(self.env)).get(valor, valor)
        if campo.type == "html":
            return markupsafe.Markup(valor)
        if campo.type in ("float", "monetary"):
            return ("%.2f" % valor).rstrip("0").rstrip(".")
        return valor

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # El padre necesita saber a dónde ir para abrir el detalle. Se escribe
        # acá porque recién ahora existe el id del hijo.
        for record in records:
            record.encounter_id.with_context(emr_allow_signed_edit=True).write(
                {"res_id": record.id}
            )
        return records

    def write(self, vals):
        """La inmutabilidad tiene que estar también acá.

        La guarda del padre no alcanza: los campos clínicos son del hijo, así
        que escribirlos no pasa por emr.encounter. Sin esto, una historia
        firmada se puede seguir editando por donde importa.
        """
        if not self.env.context.get("emr_allow_signed_edit"):
            signed = self.filtered(lambda r: r.encounter_id.state == "signed")
            if signed and set(vals) - {"encounter_id"}:
                raise UserError(
                    _(
                        "Esta historia clínica está firmada y no se puede "
                        "modificar. Para sumar información, agregá un "
                        "agregado."
                    )
                )
        return super().write(vals)

    def unlink(self):
        if self.filtered(lambda r: r.encounter_id.state != "draft"):
            raise UserError(
                _("No se puede borrar una historia clínica cerrada o firmada.")
            )
        return super().unlink()

    def action_close(self):
        return self.mapped("encounter_id").action_close()

    def action_sign(self):
        return self.mapped("encounter_id").action_sign()

    # ------------------------------------------------------------------
    # Salidas de la atención
    #
    # El profesional abrió la historia clínica y puede terminar de tres
    # maneras. Solo una es "atendido".
    # ------------------------------------------------------------------
    def _action_back_to_queue(self):
        """Devuelve al profesional a la cola de atención.

        Las acciones que cierran la atención sin haberla registrado —el que no
        entró y el que vuelve a la sala— tienen que dejarlo mirando a quién
        sigue, no en el formulario de una historia clínica que acaba de dejar.
        Sin esto el cliente se queda en un registro archivado o desvinculado.
        """
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "emr.sale_order_action_queue"
        )
        # `main` y no `current`: no es un paso más del camino sino volver al
        # principio, y así se limpia el rastro. Sin eso queda en el camino la
        # historia que se abandonó, y el botón de atrás lleva a un registro
        # archivado o ya desvinculado del turno.
        action["target"] = "main"
        return action

    def action_no_show(self):
        """El paciente no entró al consultorio.

        La historia clínica se archiva y se desvincula del turno: no hubo
        atención, así que no tiene que quedar colgada del paciente. Se archiva
        y no se borra porque es un registro clínico —aunque esté vacío— y
        porque borrar el registro que el usuario tiene abierto rompe la
        navegación del cliente.
        """
        self.ensure_one()
        order = self.encounter_id.order_id
        self.encounter_id.with_context(emr_allow_signed_edit=True).write(
            {"active": False, "order_id": False}
        )
        if order:
            order.encounter_id = False
            order._emr_no_show_from_attention()
        return self._action_back_to_queue()

    def action_wait(self):
        """Vuelve a la sala y sigue con otro.

        Guarda lo cargado hasta acá y devuelve el paciente a la cola con la
        espera arrancando de nuevo: el rato que estuvo adentro no cuenta como
        espera.
        """
        self.ensure_one()
        order = self.encounter_id.order_id
        if order:
            order.write({"confirmed_datetime": fields.Datetime.now()})
            order._set_appointment_state("confirmed")
        return self._action_back_to_queue()

    def action_retype(self):
        """Abre el asistente para registrar la atención en otro tipo."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Cambiar el tipo de historia clínica"),
            "res_model": "emr.encounter.retype",
            "view_mode": "form",
            "target": "new",
            "context": {"default_encounter_id": self.encounter_id.id},
        }

