##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from datetime import date, timedelta

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo import Command, fields


@tagged("post_install", "-at_install")
class TestVeterinary(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.species_dog = cls.env.ref("emr_veterinary.species_dog")
        cls.species_cat = cls.env.ref("emr_veterinary.species_cat")
        cls.owner = cls.env["res.partner"].create({"name": "Ana Dueña"})
        cls.pet = cls.env["emr.pet"].create({
            "name": "Lola",
            "species_id": cls.species_dog.id,
            "owner_id": cls.owner.id,
            "sex": "female",
            "birth_date": date(2024, 1, 15),
        })
        cls.vet = cls.env["res.partner"].create({
            "name": "Dr. Ruiz",
            "is_practitioner": True,
        })
        cls.template = cls.env.ref(
            "emr_veterinary.sale_order_template_consulta_veterinaria"
        )
        cls.encounter_type = cls.env.ref("emr_veterinary.encounter_type_veterinary")

    def test_species_data_and_age(self):
        self.assertEqual(self.species_dog.name, "Perro")
        self.assertEqual(self.species_cat.name, "Gato")
        Pet = self.env["emr.pet"]
        self.assertEqual(Pet._format_age(date(2024, 1, 15), date(2026, 11, 25)), "2 años y 10 meses")
        self.assertEqual(Pet._format_age(date(2025, 11, 25), date(2026, 11, 25)), "1 año")
        self.assertFalse(Pet._format_age(False, date(2026, 11, 25)))
        self.assertIn("año", self.pet.age)

    def test_breed_must_match_species(self):
        siames = self.env["emr.pet.breed"].create({
            "name": "Siamés",
            "species_id": self.species_cat.id,
        })
        with self.assertRaises(ValidationError):
            self.pet.write({"breed_id": siames.id})

    def test_microchip_unique(self):
        self.pet.microchip = "CHIP-900"
        with self.assertRaises(ValidationError):
            self.env["emr.pet"].create({
                "name": "Otra",
                "species_id": self.species_dog.id,
                "owner_id": self.owner.id,
                "microchip": "CHIP-900",
            })

    def test_appointment_bills_owner_who_is_not_a_patient(self):
        self.assertFalse(self.owner.is_patient)
        order = self.env["sale.order"].create({
            "partner_id": self.env["res.partner"].create({"name": "Alguien"}).id,
            "pet_id": self.pet.id,
            "is_appointment": True,
            "practitioner_id": self.vet.id,
        })
        self.assertEqual(order.partner_id, self.owner)
        self.assertEqual(order.pet_id, self.pet)
        self.assertIn(self.pet.name, order.appointment_calendar_title)

        with self.assertRaises(ValidationError):
            self.env["sale.order"].create({
                "partner_id": self.owner.id,
                "is_appointment": True,
            })

        patient = self.env["res.partner"].create({
            "name": "Paciente humano",
            "is_patient": True,
        })
        human = self.env["sale.order"].create({
            "partner_id": patient.id,
            "is_appointment": True,
        })
        self.assertEqual(human.partner_id, patient)
        self.assertFalse(human.pet_id)

    def test_deceased_pet_cannot_be_booked(self):
        self.pet.deceased = True
        with self.assertRaises(UserError):
            self.env["sale.order"].create({
                "partner_id": self.owner.id,
                "pet_id": self.pet.id,
                "is_appointment": True,
            })

    def test_book_wizard_ignores_insurer_pricelist(self):
        insurer_pl = self.env["product.pricelist"].create({"name": "Arancel obra social"})
        particular = self.env["product.pricelist"].create({"name": "Particular vet"})
        insurer = self.env["res.partner"].create({
            "name": "Obra social",
            "is_company": True,
            "is_insurer": True,
            "insurer_pricelist_id": insurer_pl.id,
        })
        self.owner.write({
            "insurer_id": insurer.id,
            "insurance_member_number": "A-100",
            "property_product_pricelist": particular.id,
        })
        wizard = self.env["emr.appointment.book"].with_context(emr_veterinary=True).create({
            "pet_id": self.pet.id,
            "partner_id": self.owner.id,
            "practitioner_id": self.vet.id,
            "start": fields.Datetime.now(),
            "sale_order_template_id": self.template.id,
            "appointment_mode": "scheduled",
        })
        vals = wizard._prepare_order_vals()
        self.assertEqual(vals["partner_id"], self.owner.id)
        self.assertEqual(vals["pet_id"], self.pet.id)
        self.assertEqual(vals["pricelist_id"], particular.id)
        self.assertNotEqual(vals["pricelist_id"], insurer_pl.id)

        charge = self.env["emr.appointment.charge"].get_view()["arch"]
        self.assertIn("pet_id or not insurer_id", charge)
        self.assertIn("pet_id or not pricelist_id", charge)
        book = self.env["emr.appointment.book"].get_view()["arch"]
        self.assertIn("emr_veterinary", book)
        self.assertNotIn("insurance_member_number", book)

    def test_encounter_weight_history_signature_and_panel(self):
        other = self.env["emr.pet"].create({
            "name": "Mora",
            "species_id": self.species_cat.id,
            "owner_id": self.owner.id,
        })
        visit = self._visit(self.pet, reason="Tos", weight=8.5, temperature=38.6)
        other_visit = self._visit(other, reason="Control")
        self.assertEqual(visit.partner_id, self.owner)
        self.assertEqual(visit.encounter_type_id, self.encounter_type)
        self.assertEqual(self.pet.weight_ids.weight, 8.5)

        entries = self.env["emr.encounter"].with_context(
            emr_pet_id=self.pet.id
        ).get_patient_history(self.owner.id)
        ids = [item["id"] for item in entries]
        self.assertIn(visit.encounter_id.id, ids)
        self.assertNotIn(other_visit.encounter_id.id, ids)
        self.assertTrue(entries[0]["html"])

        visit.action_close()
        visit.action_sign()
        with self.assertRaises(UserError):
            visit.write({"reason": "Otro motivo"})

    def test_consumption_stock_and_invoice_to_owner(self):
        product = self.env["product.product"].create({
            "name": "Amoxicilina",
            "type": "consu",
            "is_storable": True,
            "tracking": "lot",
            "use_expiration_date": True,
            "veterinary_kind": "medicine",
            "categ_id": self.env.ref("emr_veterinary.product_category_medicine").id,
            "list_price": 1000,
        })
        self.assertEqual(product.categ_id.name, "Medicamentos")
        expiration = fields.Datetime.now() + timedelta(days=400)
        lot = self.env["stock.lot"].create({
            "name": "L-2026",
            "product_id": product.id,
        })
        lot.expiration_date = expiration
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        self.assertTrue(warehouse)
        self.env["stock.quant"]._update_available_quantity(
            product, warehouse.lot_stock_id, 10, lot_id=lot
        )
        order = self.env["sale.order"].create({
            "partner_id": self.owner.id,
            "pet_id": self.pet.id,
            "is_appointment": True,
            "practitioner_id": self.vet.id,
        })
        visit = self._visit(
            self.pet,
            order=order,
            weight=9,
            consumption_line_ids=[
                Command.create({
                    "product_id": product.id,
                    "quantity": 2,
                    "lot_id": lot.id,
                    "to_invoice": True,
                })
            ],
        )
        visit.action_close()
        line = visit.consumption_line_ids
        self.assertEqual(line.stock_move_id.state, "done")
        self.assertEqual(line.stock_move_id.product_uom_qty, 2)
        self.assertEqual(line.sale_line_id.order_id, order)
        self.assertEqual(line.sale_line_id.order_id.partner_id, self.owner)
        self.assertEqual(line.expiration_date, lot.expiration_date)
        left = self.env["stock.quant"]._get_available_quantity(
            product, warehouse.lot_stock_id, lot_id=lot
        )
        self.assertEqual(left, 8)
        self.assertEqual(self.pet.weight_ids.filtered(lambda item: item.encounter_id == visit).weight, 9)

        visit.action_sign()
        with self.assertRaises(UserError):
            line.write({"quantity": 5})

    def test_prevention_reminder_and_prescription(self):
        product = self.env["product.product"].create({
            "name": "Antirrábica",
            "type": "service",
            "veterinary_kind": "medicine",
        })
        soon = self.env["emr.pet.prevention"].create({
            "pet_id": self.pet.id,
            "kind": "vaccine",
            "product_id": product.id,
            "date": fields.Date.context_today(self.pet),
            "next_date": fields.Date.add(fields.Date.context_today(self.pet), days=3),
            "lot_id": False,
        })
        later = self.env["emr.pet.prevention"].create({
            "pet_id": self.pet.id,
            "kind": "deworming",
            "product_id": product.id,
            "date": fields.Date.context_today(self.pet),
            "next_date": fields.Date.add(fields.Date.context_today(self.pet), days=40),
        })
        self.env["emr.pet.prevention"]._cron_send_reminders()
        self.assertTrue(soon.activity_id)
        self.assertEqual(soon.activity_id.res_id, self.pet.id)
        self.assertFalse(later.reminder_sent)
        self.env["emr.pet.prevention"]._cron_send_reminders()
        self.assertEqual(len(self.pet.activity_ids), 1)

        visit = self._visit(self.pet, reason="Vacuna")
        prescription = self.env["emr.veterinary.prescription"].create({
            "encounter_id": visit.id,
            "indications": "Con la comida",
            "line_ids": [Command.create({
                "name": "Amoxicilina",
                "dosage": "1 comprimido",
                "instructions": "cada 12 horas",
            })],
        })
        html, _report_type = self.env["ir.actions.report"]._render_qweb_html(
            "emr_veterinary.report_prescription", prescription.ids
        )
        text = html.decode() if isinstance(html, bytes) else str(html)
        self.assertIn("Amoxicilina", text)
        self.assertIn("Con la comida", text)
        self.assertNotIn("Obra social", text)
        self.assertIn(self.owner.name, text)

        history_html, _report_type = self.env["ir.actions.report"]._render_qweb_html(
            "emr_veterinary.report_pet_history", self.pet.ids
        )
        text = history_html.decode() if isinstance(history_html, bytes) else str(history_html)
        self.assertIn("Lola", text)
        self.assertIn("Antirrábica", text)
        self.assertNotIn("Obra social", text)

    def test_appointment_opens_veterinary_encounter(self):
        order = self.env["sale.order"].create({
            "partner_id": self.owner.id,
            "pet_id": self.pet.id,
            "is_appointment": True,
            "practitioner_id": self.vet.id,
        })
        order._emr_apply_template(self.template)
        action = order._open_encounter()
        visit = self.env["emr.encounter.veterinary"].browse(action["res_id"])
        self.assertEqual(visit.pet_id, self.pet)
        self.assertEqual(visit.partner_id, self.owner)
        self.assertEqual(visit.res_model, "emr.encounter.veterinary")
        self.assertEqual(order.encounter_id, visit.encounter_id)

    def _visit(self, pet, order=None, **extra):
        vals = {
            "pet_id": pet.id,
            "practitioner_id": self.vet.id,
            "encounter_type_id": self.encounter_type.id,
            "order_id": order.id if order else False,
        }
        vals.update(extra)
        return self.env["emr.encounter.veterinary"].create(vals)
