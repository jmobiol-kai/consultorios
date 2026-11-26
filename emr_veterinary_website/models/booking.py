##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Tope de la página pública. La recepción no entra en esta cuenta: solo
# los turnos que dejaron IP, que son los del sitio.
_WINDOW = timedelta(hours=1)
_MAX_PER_IP = 5
_MAX_PER_EMAIL = 3
_HORIZON = timedelta(days=21)


def _digits(value):
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


class EmrVeterinaryWebsiteBooking(models.AbstractModel):
    """Arma el turno público. El controlador solo muestra la página.

    No usa el asistente de recepción: ese encadena el cobro. Acá el turno
    queda programado, el hueco ocupado, y el dueño no tiene que ser paciente.
    """

    _name = "emr.veterinary.website.booking"
    _description = "Pedido de turno desde el sitio"

    @api.model
    def form_values(self, practitioner_id=None, post=None):
        post = post or {}
        practitioners = self.env["res.partner"].search(
            [("is_practitioner", "=", True)], order="name"
        )
        chosen = practitioners.browse(_as_int(practitioner_id)).exists()
        if chosen not in practitioners:
            chosen = self.env["res.partner"]
        now = fields.Datetime.now()
        domain = [
            ("available", "=", True),
            ("slot_type", "=", "scheduled"),
            ("start", ">=", now),
            ("start", "<=", now + _HORIZON),
        ]
        if chosen:
            domain.append(("practitioner_id", "=", chosen.id))
        return {
            "practitioners": practitioners,
            "practitioner": chosen,
            "practices": self.env["sale.order.template"].search(
                [("is_appointment", "=", True)], order="name"
            ),
            "slots": self.env["emr.slot"].search(
                domain, order="start, practitioner_id", limit=80
            ),
            "species": self.env["emr.pet.species"].search([], order="name"),
            "breeds": self.env["emr.pet.breed"].search([], order="name"),
            "post": post,
            "error": False,
        }

    @api.model
    def book(self, post, ip=None):
        """Crea dueño, mascota y turno, o reutiliza los que ya están.

        Devuelve la orden, o ``None`` si el señuelo antispam vino lleno:
        no se guarda nada y la página igual agradece, para no avisar al robot.
        """
        post = post or {}
        if (post.get("emr_hp") or "").strip():
            return None
        email = self._clean_email(post.get("email"))
        phone = (post.get("phone") or "").strip()
        if len(_digits(phone)) < 6:
            raise UserError(_("El teléfono tiene que tener al menos 6 números."))
        self._check_rate(ip, email)
        slot = self._lock_slot(_as_int(post.get("slot_id")))
        self._check_slot(slot, _as_int(post.get("practitioner_id")))
        company = slot.company_id or self.env.company
        partner = self._find_or_create_partner(
            name=(post.get("owner_name") or "").strip(),
            email=email,
            phone=phone,
            dni=(post.get("vat") or "").strip(),
            company=company,
        )
        pet = self._find_or_create_pet(partner, post, company)
        practice = self._practice(_as_int(post.get("practice_id")))
        order = self.env["sale.order"].create({
            "partner_id": partner.id,
            "pet_id": pet.id,
            "company_id": company.id,
            "is_appointment": True,
            "practitioner_id": slot.practitioner_id.id,
            "slot_id": slot.id,
            "location_id": slot.location_id.id or False,
            "appointment_start": slot.start,
            "appointment_stop": slot.stop,
            "appointment_mode": "scheduled",
            "appointment_state": "booked",
            "emr_website_ip": ip or False,
            "note": _("Pedido de turno desde el sitio web."),
        })
        if practice:
            order._emr_apply_template(practice)
        # El estado del hueco sale del turno. Si esto falla, la transacción
        # entera vuelve atrás y el hueco sigue libre.
        slot.write({"order_id": order.id})
        order._portal_ensure_token()
        self._send_confirmation(order)
        return order

    @api.model
    def _check_rate(self, ip, email):
        since = fields.Datetime.now() - _WINDOW
        Order = self.env["sale.order"]
        if ip and Order.search_count([
            ("emr_website_ip", "=", ip),
            ("create_date", ">=", since),
            ("is_appointment", "=", True),
        ]) >= _MAX_PER_IP:
            raise UserError(
                _("Demasiados pedidos desde esta conexión. Probá más tarde.")
            )
        if Order.search_count([
            ("partner_id.email", "=ilike", email),
            ("emr_website_ip", "!=", False),
            ("create_date", ">=", since),
            ("is_appointment", "=", True),
        ]) >= _MAX_PER_EMAIL:
            raise UserError(
                _("Ya hay varios turnos pedidos con este correo. Probá más tarde.")
            )

    @api.model
    def _lock_slot(self, slot_id):
        slot = self.env["emr.slot"].browse(slot_id).exists()
        if not slot:
            raise UserError(_("Elegí un horario de la lista."))
        self.env.cr.execute(
            "SELECT id FROM emr_slot WHERE id = %s FOR UPDATE", (slot.id,)
        )
        slot.invalidate_recordset()
        return slot

    @api.model
    def _check_slot(self, slot, practitioner_id):
        if slot.slot_type != "scheduled" or not slot.available:
            raise UserError(_("Ese horario ya no está libre. Elegí otro."))
        if slot.start < fields.Datetime.now():
            raise UserError(_("Ese horario ya pasó. Elegí otro."))
        if practitioner_id and slot.practitioner_id.id != practitioner_id:
            raise UserError(_("Ese horario no es del profesional elegido."))

    @api.model
    def _clean_email(self, value):
        email = (value or "").strip()
        domain = email.split("@")[-1] if "@" in email else ""
        if " " in email or email.count("@") != 1 or "." not in domain:
            raise UserError(_("El correo no es válido."))
        return email

    @api.model
    def _dni_vals(self, dni):
        if not dni:
            return {}
        digits = _digits(dni)
        if len(digits) not in (7, 8):
            raise UserError(_("El DNI tiene que tener 7 u 8 números."))
        vals = {"vat": digits}
        if "l10n_latam_identification_type_id" in self.env["res.partner"]._fields:
            dni_type = self.env.ref("l10n_ar.it_dni", raise_if_not_found=False)
            if dni_type:
                vals["l10n_latam_identification_type_id"] = dni_type.id
        return vals

    @api.model
    def _find_or_create_partner(self, name, email, phone, dni, company):
        if len(name) < 2:
            raise UserError(_("Falta el nombre del dueño."))
        Partner = self.env["res.partner"]
        partner = Partner.search([("email", "=ilike", email)], order="id", limit=1)
        if not partner:
            matched = self._partners_by_phone(phone)
            if len(matched) == 1:
                partner = matched
        if partner:
            vals = {}
            if phone and not partner.phone:
                vals["phone"] = phone
            if email and not partner.email:
                vals["email"] = email
            if dni and not partner.vat:
                vals.update(self._dni_vals(dni))
            if vals:
                partner.write(vals)
            return partner
        vals = {
            "name": name,
            "email": email,
            "phone": phone,
            "company_id": company.id,
        }
        vals.update(self._dni_vals(dni))
        return Partner.create(vals)

    @api.model
    def _partners_by_phone(self, phone):
        """Busca por los dígitos, sin depender de espacios ni guiones."""
        needle = _digits(phone)[-8:]
        if len(needle) < 6:
            return self.env["res.partner"]
        self.env.flush_all()
        self.env.cr.execute(
            """
            SELECT id
              FROM res_partner
             WHERE regexp_replace(COALESCE(phone, ''), '\\D', '', 'g') LIKE %s
             ORDER BY id
             LIMIT 5
            """,
            ("%" + needle,),
        )
        partners = self.env["res.partner"].browse(
            row[0] for row in self.env.cr.fetchall()
        )
        return partners.filtered(lambda item: self._phone_matches(item.phone, needle))

    @api.model
    def _phone_matches(self, phone, needle):
        digits = _digits(phone)
        return bool(digits) and len(digits) >= 6 and (
            digits.endswith(needle) or needle.endswith(digits)
        )

    @api.model
    def _find_or_create_pet(self, partner, post, company):
        name = (post.get("pet_name") or "").strip()
        if len(name) < 1:
            raise UserError(_("Falta el nombre de la mascota."))
        species = self.env["emr.pet.species"].browse(
            _as_int(post.get("species_id"))
        ).exists()
        if not species:
            raise UserError(_("Elegí la especie."))
        breed = self.env["emr.pet.breed"].browse(_as_int(post.get("breed_id"))).exists()
        if breed and breed.species_id != species:
            raise UserError(_("La raza no corresponde a la especie."))
        sex = post.get("sex") or "unknown"
        if sex not in ("male", "female", "unknown"):
            raise UserError(_("Elegí el sexo de la mascota."))
        birth = self._birth_date(post.get("birth_date"))
        pets = self.env["emr.pet"].search([
            ("owner_id", "=", partner.id),
            ("species_id", "=", species.id),
            ("name", "=ilike", name),
        ])
        alive = pets.filtered(lambda pet: not pet.deceased)
        if pets and not alive:
            raise UserError(
                _(
                    "%(name)s figura como fallecida. Llamá a la clínica para el turno.",
                    name=name,
                )
            )
        if alive:
            return alive[0]
        vals = {
            "name": name,
            "species_id": species.id,
            "owner_id": partner.id,
            "sex": sex,
            "company_id": company.id,
        }
        if breed:
            vals["breed_id"] = breed.id
        if birth:
            vals["birth_date"] = birth
        return self.env["emr.pet"].create(vals)

    @api.model
    def _birth_date(self, value):
        if not (value or "").strip():
            return False
        try:
            day = fields.Date.to_date(value)
        except (ValueError, TypeError) as err:
            raise UserError(_("La fecha de nacimiento no es válida.")) from err
        today = fields.Date.context_today(self)
        if day > today:
            raise UserError(_("La fecha de nacimiento no puede ser futura."))
        if day.year < 1980:
            raise UserError(_("Revisá la fecha de nacimiento."))
        return day

    @api.model
    def _practice(self, practice_id):
        if not practice_id:
            return self.env["sale.order.template"]
        practice = self.env["sale.order.template"].browse(practice_id).exists()
        if not practice or not practice.is_appointment:
            raise UserError(_("Esa práctica no se puede reservar online."))
        return practice

    @api.model
    def _send_confirmation(self, order):
        if not order.partner_id.email:
            return
        template = self.env.ref(
            "emr_veterinary_website.mail_template_turno",
            raise_if_not_found=False,
        )
        if not template:
            return
        try:
            template.send_mail(order.id, force_send=False)
        except Exception:
            _logger.exception(
                "No se pudo encolar el mail del turno %s", order.display_name
            )
            # El turno ya está. Un mail caído no lo deshace.
            return
