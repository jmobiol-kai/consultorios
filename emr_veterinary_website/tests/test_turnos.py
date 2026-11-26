##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import HttpCase, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTurnosBooking(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.species = cls.env.ref("emr_veterinary.species_dog")
        cls.vet = cls.env["res.partner"].create({
            "name": "Dra. Web",
            "is_practitioner": True,
        })
        cls.template = cls.env.ref(
            "emr_veterinary.sale_order_template_consulta_veterinaria"
        )
        cls.Booking = cls.env["emr.veterinary.website.booking"]

    def _slot(self, hours=24):
        start = fields.Datetime.now() + timedelta(hours=hours)
        return self.env["emr.slot"].create({
            "practitioner_id": self.vet.id,
            "start": start,
            "stop": start + timedelta(minutes=30),
            "duration": 30,
            "slot_type": "scheduled",
        })

    def _post(self, slot, **extra):
        values = {
            "owner_name": "Camila Dueña",
            "phone": "11 5555 0101",
            "email": "camila.web@example.com",
            "vat": "30111222",
            "pet_name": "Rita",
            "species_id": str(self.species.id),
            "breed_id": "",
            "sex": "female",
            "birth_date": "2023-05-02",
            "slot_id": str(slot.id),
            "practice_id": str(self.template.id),
            "practitioner_id": str(self.vet.id),
            "emr_hp": "",
        }
        values.update(extra)
        return values

    def test_book_creates_owner_pet_and_occupies_the_slot(self):
        slot = self._slot()
        order = self.Booking.book(self._post(slot), ip="203.0.113.10")
        self.assertTrue(order.is_appointment)
        self.assertEqual(order.appointment_state, "booked")
        self.assertEqual(order.pet_id.name, "Rita")
        self.assertEqual(order.pet_id.species_id, self.species)
        self.assertEqual(order.partner_id, order.pet_id.owner_id)
        self.assertFalse(order.partner_id.is_patient)
        self.assertEqual(order.partner_id.email, "camila.web@example.com")
        self.assertEqual(order.partner_id.vat, "30111222")
        if "l10n_latam_identification_type_id" in order.partner_id._fields:
            self.assertEqual(
                order.partner_id.l10n_latam_identification_type_id,
                self.env.ref("l10n_ar.it_dni"),
            )
        self.assertEqual(slot.order_id, order)
        self.assertFalse(slot.available)
        self.assertTrue(order.order_line)
        mail = self.env["mail.mail"].search([
            ("model", "=", "sale.order"),
            ("res_id", "=", order.id),
        ])
        self.assertTrue(mail)

        again = self._slot(hours=30)
        reused = self.Booking.book(
            self._post(again, pet_name="rita", practice_id=""),
            ip="203.0.113.11",
        )
        self.assertEqual(reused.partner_id, order.partner_id)
        self.assertEqual(reused.pet_id, order.pet_id)
        self.assertFalse(reused.order_line)

        by_phone = self.env["res.partner"].create({
            "name": "Sin correo",
            "phone": "11 5555 7777",
        })
        phone_order = self.Booking.book(
            self._post(
                self._slot(hours=36),
                owner_name="Otro nombre",
                email="nuevo.telefono@example.com",
                phone="1155557777",
                pet_name="Tomi",
                practice_id="",
            ),
            ip="203.0.113.20",
        )
        self.assertEqual(phone_order.partner_id, by_phone)
        self.assertEqual(phone_order.partner_id.email, "nuevo.telefono@example.com")
        self.assertFalse(phone_order.partner_id.is_patient)

        with self.assertRaises(UserError):
            self.Booking.book(self._post(slot, email="otra@example.com"), ip="203.0.113.12")
        self.assertEqual(slot.order_id, order)

    def test_honeypot_and_rate_limit_do_not_create_a_turn(self):
        slot = self._slot(hours=48)
        before = self.env["sale.order"].search_count([])
        self.assertFalse(self.Booking.book(self._post(slot, emr_hp="http://spam"), ip="198.51.100.8"))
        self.assertEqual(self.env["sale.order"].search_count([]), before)
        self.assertTrue(slot.available)

        for offset in range(3):
            self.Booking.book(
                self._post(self._slot(hours=50 + offset), pet_name="Mascota %s" % offset),
                ip="198.51.100.%s" % offset,
            )
        with self.assertRaises(UserError):
            self.Booking.book(
                self._post(self._slot(hours=60), pet_name="Cuarta"),
                ip="198.51.100.99",
            )

    def test_deceased_pet_and_past_slot_are_rejected(self):
        owner = self.env["res.partner"].create({
            "name": "Dueño fallecida",
            "email": "dueno.fallecida@example.com",
            "phone": "1155550199",
        })
        self.env["emr.pet"].create({
            "name": "Negra",
            "species_id": self.species.id,
            "owner_id": owner.id,
            "deceased": True,
        })
        with self.assertRaises(UserError):
            self.Booking.book(
                self._post(
                    self._slot(hours=70),
                    owner_name="Otra persona",
                    email=owner.email,
                    pet_name="Negra",
                ),
                ip="203.0.113.40",
            )
        past = self._slot(hours=-5)
        with self.assertRaises(UserError):
            self.Booking.book(self._post(past, email="pasado@example.com"), ip="203.0.113.41")

    def test_shop_lists_retail_products_and_day_movements(self):
        website = self.env["website"].search([], limit=1)
        self.assertTrue(website)
        food = self.env["product.product"].create({
            "name": "Alimento publicado",
            "type": "consu",
            "list_price": 1500,
            "veterinary_kind": "food",
            "sale_ok": True,
            "is_published": True,
        })
        service = self.env["product.product"].create({
            "name": "Consulta publicada",
            "type": "service",
            "list_price": 8000,
            "veterinary_kind": "service",
            "sale_ok": True,
            "is_published": True,
        })
        domain = website.sale_product_domain()
        templates = self.env["product.template"].search(domain)
        self.assertIn(food.product_tmpl_id, templates)
        self.assertNotIn(service.product_tmpl_id, templates)

        order = self.env["sale.order"].create({
            "partner_id": self.env["res.partner"].create({"name": "Cliente web"}).id,
            "website_id": website.id,
            "order_line": [Command.create({
                "product_id": food.id,
                "product_uom_qty": 1,
            })],
        })
        self.env.flush_all()
        row = self.env["emr.veterinary.movement"].search([
            ("res_model", "=", "sale.order"),
            ("res_id", "=", order.id),
            ("move_type", "=", "venta"),
        ])
        self.assertEqual(len(row), 1)

        provider = self.env.ref("delivery.payment_provider_cod")
        self.assertEqual(provider.name, "Pagar al retirar")
        self.assertEqual(provider.state, "enabled")
        self.assertTrue(provider.is_published)
        self.assertEqual(provider.custom_mode, "cash_on_delivery")
        carrier = self.env.ref("emr_veterinary_website.carrier_pickup_clinic")
        self.assertTrue(carrier.is_published)
        self.assertTrue(carrier.allow_cash_on_delivery)
        self.assertEqual(carrier.fixed_price, 0)
        menu = self.env["website.menu"].search([("url", "=", "/turnos")])
        self.assertTrue(menu)

    def test_slots_payload_uses_buenos_aires_without_seconds(self):
        other = self.env["res.partner"].create({
            "name": "Lau",
            "is_practitioner": True,
            "emr_calendar_color": 2,
        })
        self.vet.emr_calendar_color = 4
        now = fields.Datetime.now().replace(minute=0, second=0, microsecond=0)
        start = now + timedelta(days=20, hours=0)
        start = start.replace(hour=18)
        local_day = (start - timedelta(hours=3)).date()
        window_start = (local_day - timedelta(days=2)).isoformat()
        window_end = (local_day + timedelta(days=2)).isoformat()
        self.env["emr.slot"].create({
            "practitioner_id": self.vet.id,
            "start": start,
            "stop": start + timedelta(minutes=30),
            "duration": 30,
            "slot_type": "scheduled",
        })
        later = start + timedelta(hours=1)
        self.env["emr.slot"].create({
            "practitioner_id": other.id,
            "start": later,
            "stop": later + timedelta(minutes=30),
            "duration": 30,
            "slot_type": "scheduled",
        })
        past = now - timedelta(days=3)
        past = past.replace(hour=18)
        self.env["emr.slot"].create({
            "practitioner_id": self.vet.id,
            "start": past,
            "stop": past + timedelta(minutes=30),
            "duration": 30,
            "slot_type": "scheduled",
        })
        payload = self.Booking.slots_payload(window_start, window_end)
        self.assertEqual(payload["timezone"], "America/Buenos_Aires")
        mine = [
            row for row in payload["slots"]
            if row["date"] == local_day.isoformat() and row["practitioner_id"] == self.vet.id
        ]
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0]["start"], "15:00")
        self.assertEqual(mine[0]["stop"], "15:30")
        self.assertNotRegex(mine[0]["start"], r":\d{2}:\d{2}")
        past_day = (past - timedelta(hours=3)).date().isoformat()
        past_payload = self.Booking.slots_payload(past_day, past_day)
        self.assertFalse(past_payload["slots"])
        filtered = self.Booking.slots_payload(window_start, window_end, professional_id=other.id)
        self.assertEqual(len(filtered["slots"]), 1)
        self.assertEqual(filtered["slots"][0]["start"], "16:00")
        self.assertEqual(filtered["practitioners"][0]["name"], "Lau")
        self.assertEqual(filtered["practitioners"][0]["color"], 2)
        self.assertTrue(filtered["practitioners"][0]["color_hex"].startswith("#"))
        with self.assertRaises(UserError):
            self.Booking.slots_payload("no-es-fecha", window_end)


@tagged("post_install", "-at_install")
class TestTurnosController(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vet = cls.env["res.partner"].create({
            "name": "Dr. Http",
            "is_practitioner": True,
        })
        start = fields.Datetime.now() + timedelta(days=2)
        cls.slot = cls.env["emr.slot"].create({
            "practitioner_id": cls.vet.id,
            "start": start,
            "stop": start + timedelta(minutes=20),
            "duration": 20,
            "slot_type": "scheduled",
        })
        cls.species = cls.env.ref("emr_veterinary.species_cat")

    def test_turnos_page_and_confirm(self):
        page = self.url_open("/turnos")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Pedir un turno", page.text)
        self.assertIn("Hoy", page.text)
        self.assertNotIn('type="radio"', page.text)
        token = page.text.partition('name="csrf_token" value="')[2].partition('"')[0]
        self.assertTrue(token)
        done = self.url_open("/turnos/confirmar", data={
            "csrf_token": token,
            "slot_id": str(self.slot.id),
            "owner_name": "Hugo Dueño",
            "phone": "1144443333",
            "email": "hugo.web@example.com",
            "pet_name": "Michi",
            "species_id": str(self.species.id),
            "sex": "male",
            "emr_hp": "",
        })
        self.assertEqual(done.status_code, 200)
        self.assertIn("Turno reservado", done.text)
        self.assertIn("Michi", done.text)
        order = self.env["sale.order"].search([
            ("partner_id.email", "=", "hugo.web@example.com"),
            ("is_appointment", "=", True),
        ])
        self.assertEqual(len(order), 1)
        self.assertEqual(order.pet_id.name, "Michi")
        self.assertEqual(self.slot.order_id, order)
        missing = self.url_open("/turnos/confirmado/%s" % order.id)
        self.assertEqual(missing.status_code, 404)

    def test_huecos_endpoint_returns_json(self):
        response = self.url_open("/turnos/huecos?start=2026-12-01&end=2026-12-07")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["timezone"], "America/Buenos_Aires")
        self.assertIn("slots", payload)
        self.assertRegex(payload["today"], r"^\d{4}-\d{2}-\d{2}$")

    def test_turnos_month_grid_tour(self):
        self.start_tour("/turnos", "emr_veterinary_website_turnos_month", login=None)
        bad = self.url_open("/turnos/huecos?start=no&end=2026-12-07")
        self.assertEqual(bad.status_code, 400)
