##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from datetime import datetime, time, timedelta

from pytz import timezone, utc

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date


# El estado que es del hueco y no del turno. El resto de los valores los
# aporta `sale.order.appointment_state`, para no tener dos vocabularios.
SLOT_OWN_STATES = [("free", "Libre"), ("blocked", "Bloqueado")]

# Un turno en estos estados ocupa la hora.
LIVE_APPOINTMENT_STATES = (
    "waitlist", "booked", "confirmed", "in_progress", "done", "validated",
)

# El turno se cayó: el hueco sigue mostrando qué pasó, pero la hora se puede
# volver a dar.
FALLEN_APPOINTMENT_STATES = ("cancelled", "no_show", "void")


class EmrSlot(models.Model):
    """Un hueco de agenda: disponibilidad, no demanda.

    Existe desde que se genera la agenda y es barato y descartable. Cuando
    aparece un paciente se crea la orden de venta, que es otra cosa: el hueco
    libre nunca es una orden.
    """

    _name = "emr.slot"
    _description = "Hueco de agenda"
    _order = "start, practitioner_id"

    practitioner_id = fields.Many2one(
        "res.partner",
        string="Profesional",
        required=True,
        index=True,
        domain=[("is_practitioner", "=", True)],
        context={"default_is_practitioner": True},
        ondelete="cascade",
    )
    start = fields.Datetime(required=True, index=True)
    stop = fields.Datetime(required=True)
    duration = fields.Integer("Duración (min)")

    location_id = fields.Many2one("emr.location", string="Locación", index=True)
    company_id = fields.Many2one(
        "res.company", required=True, index=True, default=lambda self: self.env.company
    )

    slot_type = fields.Selection(
        [
            ("scheduled", "Turno programado"),
            ("open", "Franja variable"),
            # El sobreturno no sale de la grilla: se encaja sobre ella cuando
            # hace falta, y por eso su hueco nace con el turno en vez de
            # pregenerarse. Igual queda en la agenda, que es donde se lo tiene
            # que ver.
            ("overbooked", "Sobreturno"),
        ],
        default="scheduled",
        required=True,
    )
    state = fields.Selection(
        # Un solo estado en el hueco, y absorbe las etapas del turno: en la
        # grilla se lee «Atendido» o «Cancelado», no un «Tomado» que no dice
        # en qué punto está el paciente.
        #
        # Es calculado con almacenamiento e inverse: el dueño del dato sigue
        # siendo la orden —hay turnos que podrían no tener hueco, y el hueco
        # libre no tiene orden— pero acá no puede discrepar, y escribirlo
        # desde la grilla escribe la orden. `precompute` porque es requerido:
        # sin eso el INSERT va con nulo y revienta la restricción.
        selection=lambda self: SLOT_OWN_STATES
        + self.env["sale.order"]._fields["appointment_state"].selection,
        string="Estado",
        compute="_compute_state",
        inverse="_inverse_state",
        store=True,
        readonly=False,
        precompute=True,
        required=True,
        index=True,
    )
    available = fields.Boolean(
        "Asignable",
        compute="_compute_available",
        store=True,
        index=True,
        help="Si se le puede dar un paciente. Un hueco cuyo turno se cayó "
        "—cancelado, ausente o anulado— vuelve a ser asignable sin perder el "
        "rastro de lo que pasó.",
    )
    block_reason = fields.Selection(
        [("holiday", "Feriado"), ("cancelled", "Horario cancelado")],
        string="Motivo del bloqueo",
        help="Un hueco bloqueado no se ofrece. El motivo importa para la "
        "agenda: no es lo mismo un feriado que un horario que el profesional "
        "dio de baja.",
    )

    order_id = fields.Many2one("sale.order", string="Turno", ondelete="set null")
    # A quién se atiende, para que la grilla no tenga que entrar a la orden.
    # Almacenado e indexado porque es la búsqueda más frecuente del mostrador.
    patient_id = fields.Many2one(
        "res.partner", string="Paciente", related="order_id.partner_id",
        store=True, index=True,
    )

    @api.depends("block_reason", "order_id", "order_id.appointment_state")
    def _compute_state(self):
        """El estado del hueco es el de su turno, y si no tiene, el propio.

        El orden de precedencia importa: un turno vivo gana siempre —esa hora
        está ocupada y no se discute—; si el turno se cayó, un bloqueo puesto
        a mano se ve; y si no hay ni turno ni bloqueo, el hueco está libre.
        """
        for slot in self:
            estado_turno = slot.order_id.appointment_state
            if estado_turno in LIVE_APPOINTMENT_STATES:
                slot.state = estado_turno
            elif slot.block_reason:
                slot.state = "blocked"
            elif estado_turno:
                slot.state = estado_turno
            else:
                slot.state = "free"

    def _inverse_state(self):
        for slot in self:
            # «Libre» y «Bloqueado» son del hueco y no se propagan. Y sin
            # orden no hay a dónde escribir.
            if slot.state in dict(SLOT_OWN_STATES) or not slot.order_id:
                continue
            slot.order_id.appointment_state = slot.state

    @api.depends("state")
    def _compute_available(self):
        """Depende de `state` y no de lo mismo que él, a propósito: así el
        cálculo sigue también a una escritura a mano del estado.

        Se enumera qué es asignable en vez de qué no lo es: un valor
        inesperado —el `taken` de una base vieja, por ejemplo— tiene que
        quedar como no asignable y no como libre. Fallar cerrado acá significa
        un hueco que no se ofrece; fallar abierto, una agenda entera que
        parece disponible.
        """
        asignables = ("free",) + FALLEN_APPOINTMENT_STATES
        for slot in self:
            slot.available = slot.state in asignables
    attendance_id = fields.Many2one(
        "resource.calendar.attendance", string="Franja de origen", ondelete="set null"
    )

    display_name = fields.Char(compute="_compute_display_name")

    # La grilla muestra el mismo momento dos veces: la hora grande, que es lo
    # que se lee de un vistazo, y el día chiquito. Se calculan como texto en la
    # zona horaria del usuario en vez de pelear con el formato del widget.
    hour_display = fields.Char("Hora", compute="_compute_time_display")
    date_display = fields.Char("Día", compute="_compute_time_display")

    _slot_uniq = models.Constraint(
        "UNIQUE (practitioner_id, start, attendance_id)",
        "Ya existe ese hueco para el profesional. La generación es "
        "idempotente y no debería duplicar.",
    )

    @api.depends("practitioner_id", "start")
    def _compute_display_name(self):
        for slot in self:
            slot.display_name = "%s - %s" % (
                slot.practitioner_id.name or "",
                fields.Datetime.to_string(slot.start) or "",
            )

    @api.depends("start")
    def _compute_time_display(self):
        for slot in self:
            if not slot.start:
                slot.hour_display = slot.date_display = ""
                continue
            local = fields.Datetime.context_timestamp(slot, slot.start)
            slot.hour_display = local.strftime("%H:%M")
            slot.date_display = format_date(
                self.env, local.date(), date_format="EEE dd/MM"
            )

    # ------------------------------------------------------------------
    # Generación
    # ------------------------------------------------------------------
    @api.model
    def _generate_for_practitioner(self, practitioner, date_from, date_to):
        """Materializa los huecos de un profesional entre dos fechas.

        Recorre cada franja de su agenda de la hora de inicio a la de fin en
        pasos del tamaño de la duración, y crea un hueco por paso.

        Es idempotente: no duplica huecos ya generados ni toca los tomados.
        Se puede volver a correr sin pensarlo, que es la diferencia con el
        sistema que reemplaza.
        """
        practitioner.ensure_one()
        calendar = practitioner.resource_calendar_id
        if not calendar:
            raise UserError(
                _("%s no tiene agenda configurada.", practitioner.display_name)
            )

        tz = timezone(calendar.tz or self.env.user.tz or "UTC")
        existing = set(
            self.search(
                [
                    ("practitioner_id", "=", practitioner.id),
                    ("start", ">=", datetime.combine(date_from, time.min)),
                    ("start", "<=", datetime.combine(date_to, time.max)),
                ]
            ).mapped(lambda s: (s.start, s.attendance_id.id))
        )

        leaves = calendar.leave_ids.filtered(
            lambda leave: not leave.resource_id
            or leave.resource_id == practitioner.resource_id
        )

        vals_list = []
        day = date_from
        while day <= date_to:
            for attendance in calendar.attendance_ids:
                # En el widget de secciones conviven filas que no son franjas.
                if attendance.display_type:
                    continue
                if int(attendance.dayofweek) != day.weekday():
                    continue
                vals_list += self._prepare_day_slots(
                    practitioner, attendance, day, tz, leaves, existing
                )
            day += timedelta(days=1)

        return self.create(vals_list) if vals_list else self.browse()

    @api.model
    def _prepare_day_slots(self, practitioner, attendance, day, tz, leaves, existing):
        """Los huecos de una franja en un día concreto."""
        duration = attendance.slot_duration or 15
        company = practitioner.company_id or self.env.company

        start_local = tz.localize(
            datetime.combine(day, time.min)
            + timedelta(hours=attendance.hour_from)
        )
        stop_local = tz.localize(
            datetime.combine(day, time.min) + timedelta(hours=attendance.hour_to)
        )
        window_start = start_local.astimezone(utc).replace(tzinfo=None)
        window_stop = stop_local.astimezone(utc).replace(tzinfo=None)

        # La franja variable no genera nada por adelantado.
        #
        # No tiene sentido materializar una ventana de ocho horas como si
        # fuera un turno: en demanda el hueco nace cuando llega el paciente,
        # con la duración de referencia de la franja. Ver _create_demand_slot.
        if attendance.slot_type == "open":
            return []

        steps = []
        cursor = window_start
        delta = timedelta(minutes=duration)
        while cursor + delta <= window_stop:
            steps.append((cursor, cursor + delta))
            cursor += delta

        vals_list = []
        for slot_start, slot_stop in steps:
            if (slot_start, attendance.id) in existing:
                continue
            blocked = any(
                leave.date_from <= slot_start < leave.date_to for leave in leaves
            )
            vals_list.append(
                {
                    "practitioner_id": practitioner.id,
                    "start": slot_start,
                    "stop": slot_stop,
                    "duration": int((slot_stop - slot_start).total_seconds() // 60),
                    "location_id": attendance.location_id.id or False,
                    "company_id": company.id,
                    "slot_type": attendance.slot_type,
                    "attendance_id": attendance.id,
                    "block_reason": "holiday" if blocked else False,
                }
            )
        return vals_list

    # ------------------------------------------------------------------
    # Demanda
    # ------------------------------------------------------------------
    @api.model
    def _demand_attendance(self, practitioner, when):
        """La franja de demanda del profesional en ese momento."""
        calendar = practitioner.resource_calendar_id
        if not calendar:
            return self.env["resource.calendar.attendance"]
        tz = timezone(calendar.tz or self.env.user.tz or "UTC")
        local = when.astimezone(tz) if when.tzinfo else utc.localize(when).astimezone(tz)
        hour = local.hour + local.minute / 60.0
        return calendar.attendance_ids.filtered(
            lambda a: not a.display_type
            and a.slot_type == "open"
            and int(a.dayofweek) == local.weekday()
            and a.hour_to > hour
        )[:1]

    @api.model
    def _attendance_at(self, practitioner, when):
        """La franja del profesional que cubre ese momento, del tipo que sea.

        Se usa para tomarle prestada la duración y la locación a un hueco que
        no nació de la grilla. El de demanda es el mismo filtro pero acotado a
        las franjas variables.
        """
        calendar = practitioner.resource_calendar_id
        if not calendar:
            return self.env["resource.calendar.attendance"]
        tz = timezone(calendar.tz or self.env.user.tz or "UTC")
        local = when.astimezone(tz) if when.tzinfo else utc.localize(when).astimezone(tz)
        hour = local.hour + local.minute / 60.0
        return calendar.attendance_ids.filtered(
            lambda a: not a.display_type
            and int(a.dayofweek) == local.weekday()
            and a.hour_from <= hour < a.hour_to
        )[:1]

    # ------------------------------------------------------------------
    # Sobreturno
    # ------------------------------------------------------------------
    @api.model
    def _overbooking_day_bounds(self, practitioner, when):
        """El día del profesional, en su zona horaria y en UTC.

        El tope es por día y el día es el suyo, no el del servidor: contar en
        UTC le partiría el día al medio a cualquiera que atienda de tarde.
        """
        calendar = practitioner.resource_calendar_id
        tz = timezone(
            (calendar.tz if calendar else None) or self.env.user.tz or "UTC"
        )
        local = when.astimezone(tz) if when.tzinfo else utc.localize(when).astimezone(tz)
        day_start = tz.localize(datetime.combine(local.date(), time.min))
        day_stop = day_start + timedelta(days=1)
        return (
            day_start.astimezone(utc).replace(tzinfo=None),
            day_stop.astimezone(utc).replace(tzinfo=None),
        )

    @api.model
    def _overbooking_count(self, practitioner, when):
        """Cuántos sobreturnos vivos tiene ese día.

        Los caídos no cuentan: un sobreturno cancelado no se dio, así que no
        consume el cupo del día.
        """
        day_start, day_stop = self._overbooking_day_bounds(practitioner, when)
        return self.search_count(
            [
                ("practitioner_id", "=", practitioner.id),
                ("slot_type", "=", "overbooked"),
                ("start", ">=", day_start),
                ("start", "<", day_stop),
                ("state", "in", list(LIVE_APPOINTMENT_STATES)),
            ]
        )

    @api.model
    def _create_overbooking_slot(self, practitioner, when, location=None):
        """Materializa el hueco de un sobreturno.

        No se pregenera —no hay grilla de sobreturnos— pero tampoco queda
        fuera de la agenda: se crea acá, con la hora que se le da, y desde ese
        momento se ve en la grilla como cualquier otro hueco. Sin
        `attendance_id`, porque no nació de ninguna franja: eso además lo deja
        afuera de la restricción de unicidad, así que dos sobreturnos pueden
        compartir la hora, que es justamente lo que un sobreturno hace.
        """
        practitioner.ensure_one()
        tope = practitioner.overbooking_daily_limit
        if tope:
            dados = self._overbooking_count(practitioner, when)
            if dados >= tope:
                raise UserError(
                    _(
                        "%(practitioner)s ya dio sus %(tope)s sobreturnos de "
                        "ese día. Si hace falta uno más, lo autoriza él "
                        "subiéndose el tope en su ficha.",
                        practitioner=practitioner.display_name,
                        tope=tope,
                    )
                )

        attendance = self._attendance_at(practitioner, when)
        duration = attendance.slot_duration or 15
        return self.create(
            {
                "practitioner_id": practitioner.id,
                "start": when,
                "stop": when + timedelta(minutes=duration),
                "duration": duration,
                "location_id": (
                    location.id if location else attendance.location_id.id or False
                ),
                "company_id": (practitioner.company_id or self.env.company).id,
                "slot_type": "overbooked",
            }
        )

    @api.model
    def _create_demand_slot(self, practitioner):
        """Crea el hueco del próximo paciente por demanda.

        En demanda no hay grilla: el hueco nace cuando alguien llega. Se lo
        ubica en el primer momento libre de acá en adelante, después del
        último que ya está esperando, y dura lo que dice la franja.
        """
        practitioner.ensure_one()
        now = fields.Datetime.now()
        attendance = self._demand_attendance(practitioner, now)
        if not attendance:
            raise UserError(
                _(
                    "%s no tiene una franja de demanda abierta en este momento.",
                    practitioner.display_name,
                )
            )

        calendar = practitioner.resource_calendar_id
        tz = timezone(calendar.tz or self.env.user.tz or "UTC")
        local_now = utc.localize(now).astimezone(tz)
        day = local_now.date()

        window_start = (
            tz.localize(datetime.combine(day, time.min) + timedelta(hours=attendance.hour_from))
            .astimezone(utc)
            .replace(tzinfo=None)
        )
        window_stop = (
            tz.localize(datetime.combine(day, time.min) + timedelta(hours=attendance.hour_to))
            .astimezone(utc)
            .replace(tzinfo=None)
        )

        # Después del último que ya está en la cola de hoy.
        last = self.search(
            [
                ("practitioner_id", "=", practitioner.id),
                ("attendance_id", "=", attendance.id),
                ("start", ">=", window_start),
                ("start", "<", window_stop),
            ],
            order="stop desc",
            limit=1,
        )
        start = max(now, window_start, last.stop or window_start)

        # PENDIENTE: la duración tendría que salir de la práctica, no de la
        # franja. En demanda, una colonoscopía ocupa 40 minutos y un banding
        # 15, y eso recién se sabe cuando se elige qué se le va a hacer al
        # paciente — o sea en el asistente de asignación, no acá.
        #
        # Cómo resolverlo: un campo de duración en el producto o en el tipo de
        # turno, y que el asistente redimensione el hueco al elegirlo. La
        # duración de la franja queda como valor por defecto para el momento
        # en que todavía no se sabe la práctica.
        #
        # Redimensionar no desacomoda nada: acá no hay un turno siguiente al
        # que correr, porque cada hueco nace cuando llega su paciente. El que
        # venga después simplemente arranca más tarde. El único límite es que
        # la ventana se llene, y eso ya está contemplado más abajo.
        duration = attendance.slot_duration or 15
        stop = start + timedelta(minutes=duration)
        if stop > window_stop:
            raise UserError(
                _("Ya no entra otro paciente en la franja de demanda de hoy.")
            )

        return self.create(
            {
                "practitioner_id": practitioner.id,
                "start": start,
                "stop": stop,
                "duration": duration,
                "location_id": attendance.location_id.id or False,
                "company_id": (practitioner.company_id or self.env.company).id,
                "slot_type": "open",
                "attendance_id": attendance.id,
            }
        )

    @api.model
    def _cron_generate_slots(self):
        """Mantiene la ventana móvil de agenda.

        Genera hacia adelante lo que falte para cada profesional con agenda.
        """
        practitioners = self.env["res.partner"].search(
            [("is_practitioner", "=", True), ("resource_calendar_id", "!=", False)]
        )
        today = fields.Date.context_today(self)
        for practitioner in practitioners:
            days = practitioner.slot_generation_days or 60
            self._generate_for_practitioner(
                practitioner, today, today + timedelta(days=days)
            )
        return True

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def action_block(self, reason="cancelled"):
        """Da de baja el horario. El estado se deriva del motivo."""
        ocupados = self.filtered(
            lambda s: s.order_id.appointment_state in LIVE_APPOINTMENT_STATES
        )
        if ocupados:
            raise UserError(
                _("No se puede bloquear un hueco que ya tiene un turno asignado.")
            )
        return self.write({"block_reason": reason})

    def action_free(self):
        """Saca el bloqueo. Si el hueco tuvo un turno que se cayó, vuelve a
        mostrar ese estado —cancelado o ausente— y sigue siendo asignable."""
        ocupados = self.filtered(
            lambda s: s.order_id.appointment_state in LIVE_APPOINTMENT_STATES
        )
        if ocupados:
            raise UserError(_("Ese hueco tiene un turno: primero hay que cancelarlo."))
        return self.write({"block_reason": False})

    def action_split(self):
        """Parte el hueco en dos.

        Sirve para meter a alguien más en una franja que quedó grande, sin
        tener que rehacer la agenda del profesional. El original se acorta a
        la primera mitad y se crea uno nuevo con la segunda.

        Los minutos impares van al segundo: partir uno de 15 da 7 y 8, no 7 y
        7 dejando un minuto en el aire.
        """
        self.ensure_one()
        if self.state != "free":
            raise UserError(
                _("Solo se puede partir un hueco libre.")
            )
        total = int((self.stop - self.start).total_seconds() // 60)
        if total < 2:
            raise UserError(
                _("Este hueco dura %s minuto y no se puede partir.", total)
            )

        middle = self.start + timedelta(minutes=total // 2)
        second = self.copy(
            {
                "start": middle,
                "stop": self.stop,
                "duration": total - total // 2,
                "order_id": False,
            }
        )
        self.write({"stop": middle, "duration": total // 2})
        return second

    def action_charge_order(self):
        """Abre el cobro del turno de este hueco.

        Es el mismo asistente que desde la orden: la grilla no es una interfaz
        aparte, es otra puerta a lo mismo.
        """
        self.ensure_one()
        if not self.order_id:
            raise UserError(_("Este hueco todavía no tiene un turno asignado."))
        return self.order_id.action_appointment_confirm()

    def action_cancel_order(self):
        """Cancela el turno de este hueco y lo devuelve a la grilla.

        Es la contraparte de `action_book`: sin esto, un hueco asignado y sin
        cobrar queda tomado para siempre y el horario se pierde. Lo de fondo
        lo hace la orden, que es la que sabe qué anular.
        """
        self.ensure_one()
        if not self.order_id:
            raise UserError(_("Este hueco no tiene un turno para cancelar."))
        return self.order_id.action_appointment_cancel()

    # ------------------------------------------------------------------
    # La agenda de un profesional, semana por semana
    # ------------------------------------------------------------------
    @api.model
    def _emr_agenda_action(self, profesional=None, ubicacion=None,
                           desplazamiento=0):
        """La agenda de un profesional o de una sala, semana por semana.

        Los dos ejes son opcionales y se combinan: se puede mirar todo lo de
        un profesional, todo lo que pasa en una sala, o a ese profesional en
        esa sala. Es el mismo recorte con distinta pregunta.

        El desplazamiento se cuenta en semanas desde hoy: 0 es la que viene,
        -1 la anterior. Va en el contexto de la acción y de ahí lo leen los
        botones para moverse, que es la forma de que la navegación no necesite
        guardar estado en ningún lado.
        """
        hoy = fields.Date.context_today(self)
        desde = hoy + timedelta(days=7 * desplazamiento)
        hasta = desde + timedelta(days=7)

        dominio = [
            ("start", ">=", self._emr_utc(desde)),
            ("start", "<", self._emr_utc(hasta)),
        ]
        partes = []
        if profesional:
            dominio.insert(0, ("practitioner_id", "=", profesional.id))
            partes.append(profesional.display_name)
        if ubicacion:
            dominio.insert(0, ("location_id", "=", ubicacion.id))
            partes.append(ubicacion.display_name)

        return {
            "type": "ir.actions.act_window",
            "name": _(
                "Agenda de %(que)s · %(desde)s al %(hasta)s",
                que=" · ".join(partes),
                desde=format_date(self.env, desde),
                hasta=format_date(self.env, hasta),
            ),
            "res_model": "emr.slot",
            "view_mode": "kanban,list,form",
            "domain": dominio,
            "context": {
                "search_default_group_day": 1,
                "default_practitioner_id": profesional.id if profesional else False,
                "default_location_id": ubicacion.id if ubicacion else False,
                # Lo que enciende los botones de semana y les dice dónde están.
                "emr_week_nav": True,
                "emr_nav_practitioner_id": profesional.id if profesional else False,
                "emr_nav_location_id": ubicacion.id if ubicacion else False,
                "emr_nav_offset": desplazamiento,
            },
        }

    @api.model
    def _emr_utc(self, dia):
        """El comienzo de un día local, en UTC.

        `start` se guarda en UTC y el corte de la semana es local. Comparar
        contra la fecha pelada correría la ventana tres horas y dejaría los
        primeros turnos de la mañana del lado equivocado.
        """
        tz = timezone(self.env.user.tz or "UTC")
        local = tz.localize(datetime.combine(dia, time.min))
        return local.astimezone(utc).replace(tzinfo=None)

    @api.model
    def _emr_agenda_paso(self, paso):
        ctx = self.env.context
        profesional = self.env["res.partner"].browse(
            ctx.get("emr_nav_practitioner_id") or []
        )
        ubicacion = self.env["emr.location"].browse(
            ctx.get("emr_nav_location_id") or []
        )
        if not profesional and not ubicacion:
            raise UserError(_("Esta vista no es una agenda filtrada."))
        return self._emr_agenda_action(
            profesional, ubicacion, (ctx.get("emr_nav_offset") or 0) + paso
        )

    # Sin @api.model: el botón del encabezado manda los ids como primer
    # argumento, y con el decorador se cuelan como un posicional de más.
    def action_week_prev(self):
        return self._emr_agenda_paso(-1)

    def action_week_next(self):
        return self._emr_agenda_paso(1)

    def action_add_practice(self):
        """Suma una práctica al turno de este hueco.

        Sirve en cualquier estado del turno: lo que se agrega suele
        descubrirse durante la atención, no antes.
        """
        self.ensure_one()
        if not self.order_id:
            raise UserError(_("Este hueco todavía no tiene un turno asignado."))
        return self.order_id.action_add_practice()

    def action_book(self):
        """Abre el asistente para asignarle un paciente a este hueco.

        Se mira `available` y no `order_id`: un hueco cuyo turno se canceló o
        cuyo paciente no vino sigue mostrando eso en la grilla, pero la hora
        está libre y se puede volver a dar.
        """
        self.ensure_one()
        if not self.available:
            if self.state == "blocked":
                raise UserError(_("Este hueco está bloqueado."))
            raise UserError(_("Este hueco ya tiene un turno asignado."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Asignar turno"),
            "res_model": "emr.appointment.book",
            "view_mode": "form",
            "target": "new",
            "context": {"default_slot_id": self.id},
        }
