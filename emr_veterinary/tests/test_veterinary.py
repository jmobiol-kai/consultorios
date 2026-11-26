##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from datetime import date, timedelta

from lxml import etree

from odoo.exceptions import UserError, ValidationError
from odoo.service.model import call_kw
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
            "name": "Raza de prueba",
            "species_id": self.species_cat.id,
        })
        with self.assertRaises(ValidationError):
            self.pet.write({"breed_id": siames.id})

    def test_breed_catalog_loads_for_dog_and_cat(self):
        dogs = self.env["emr.pet.breed"].search([("species_id", "=", self.species_dog.id)])
        cats = self.env["emr.pet.breed"].search([("species_id", "=", self.species_cat.id)])
        self.assertGreaterEqual(len(dogs), 40)
        self.assertLessEqual(len(dogs), 60)
        self.assertGreaterEqual(len(cats), 20)
        self.assertLessEqual(len(cats), 30)
        self.assertEqual(len(dogs), len(set(dogs.mapped("name"))))
        self.assertEqual(len(cats), len(set(cats.mapped("name"))))
        for name in ("Callejero", "Dogo Argentino", "Ovejero Alemán", "Labrador Retriever",
                     "Golden Retriever", "Caniche", "Bulldog Francés"):
            self.assertIn(name, dogs.mapped("name"))
        for name in ("Callejero", "Siamés", "Persa", "Maine Coon", "Común Europeo"):
            self.assertIn(name, cats.mapped("name"))
        dogo = self.env.ref("emr_veterinary.breed_dog_dogo_argentino")
        siames = self.env.ref("emr_veterinary.breed_cat_siames")
        self.assertEqual(dogo.species_id, self.species_dog)
        self.assertEqual(siames.species_id, self.species_cat)
        self.assertEqual(
            self.env.ref("emr_veterinary.breed_dog_callejero").name,
            self.env.ref("emr_veterinary.breed_cat_callejero").name,
        )

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

    def test_addenda_tab_only_when_the_consultation_is_signed(self):
        arch = self.env["emr.encounter.veterinary"].get_view(view_type="form")["arch"]
        page = etree.fromstring(arch.encode()).xpath("//page[@name='addenda']")
        self.assertEqual(len(page), 1)
        self.assertEqual(page[0].get("string"), "Agregados")
        self.assertEqual(page[0].get("invisible"), "state != 'signed'")
        base = self.env.ref("emr.emr_encounter_view_form_base").arch
        base_page = etree.fromstring(base.encode()).xpath("//page[@name='addenda']")
        self.assertEqual(len(base_page), 1)
        self.assertFalse(base_page[0].get("invisible"))

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

    def test_consultorio_menu_hidden_and_vet_reuses_emr_actions(self):
        reception = self.env["res.users"].create({
            "name": "Recepción vet",
            "login": "recepcion.vet.test",
            "group_ids": [Command.set([
                self.env.ref("emr.group_emr_reception").id,
            ])],
        })
        manager = self.env["res.users"].create({
            "name": "Admin clínica",
            "login": "admin.vet.test",
            "group_ids": [Command.set([
                self.env.ref("emr.group_emr_manager").id,
            ])],
        })
        Menu = self.env["ir.ui.menu"]
        root = self.env.ref("emr.menu_emr_root")
        vet_root = self.env.ref("emr_veterinary.menu_emr_veterinary_root")

        reception_menus = Menu.with_user(reception)._visible_menu_ids(False)
        self.assertNotIn(root.id, reception_menus)
        self.assertNotIn(self.env.ref("emr.menu_emr_patients").id, reception_menus)
        self.assertIn(vet_root.id, reception_menus)
        self.assertIn(
            self.env.ref("emr_veterinary.menu_emr_veterinary_practitioners").id,
            reception_menus,
        )

        manager_menus = Menu.with_user(manager)._visible_menu_ids(False)
        self.assertNotIn(root.id, manager_menus)
        for xmlid in (
            "emr_veterinary.menu_emr_veterinary_procedures",
            "emr_veterinary.menu_emr_veterinary_locations",
            "emr_veterinary.menu_emr_veterinary_movements",
        ):
            self.assertIn(self.env.ref(xmlid).id, manager_menus)
        self.assertFalse(self.env.ref(
            "emr_veterinary.menu_emr_veterinary_attentions", raise_if_not_found=False
        ))
        self.assertTrue(self.env.ref("emr.emr_encounter_action"))

        admin_menus = Menu.with_user(self.env.ref("base.user_admin"))._visible_menu_ids(False)
        self.assertIn(root.id, admin_menus)

        self.assertEqual(
            self.env.ref("emr_veterinary.menu_emr_veterinary_practitioners").action,
            self.env.ref("emr.res_partner_action_practitioner"),
        )
        self.assertEqual(
            self.env.ref("emr_veterinary.menu_emr_veterinary_procedures").action,
            self.env.ref("emr.product_template_action_procedure"),
        )
        self.assertEqual(
            self.env.ref("emr_veterinary.menu_emr_veterinary_locations").action,
            self.env.ref("emr.emr_location_action"),
        )

    def test_color_catalog_and_legacy_text(self):
        dogs = self.env["emr.pet.color"].search([("species_id", "=", self.species_dog.id)])
        cats = self.env["emr.pet.color"].search([("species_id", "=", self.species_cat.id)])
        self.assertIn("Negro", dogs.mapped("name"))
        self.assertIn("Negro y fuego", dogs.mapped("name"))
        self.assertIn("Merle", dogs.mapped("name"))
        self.assertIn("Carey", cats.mapped("name"))
        self.assertIn("Colorpoint", cats.mapped("name"))
        self.assertIn("Atigrado naranja", cats.mapped("name"))
        cat_black = self.env.ref("emr_veterinary.color_cat_negro")
        with self.assertRaises(ValidationError):
            self.pet.write({"color_id": cat_black.id})
        self.pet.color_note = "  dorado "
        self.pet._match_legacy_colors()
        self.assertEqual(self.pet.color_id, self.env.ref("emr_veterinary.color_dog_dorado"))
        self.assertFalse(self.pet.color_note)
        self.pet.write({"color_id": False, "color_note": "turquesa imposible"})
        self.pet._match_legacy_colors()
        self.assertFalse(self.pet.color_id)
        self.assertEqual(self.pet.color_note, "turquesa imposible")

    def test_new_consultation_from_empty_history(self):
        self.assertFalse(self.pet.encounter_ids)
        self.env.user.partner_id.write({"is_practitioner": True})
        action = self.pet.action_new_consultation()
        self.assertEqual(action["res_model"], "emr.encounter.veterinary")
        self.assertEqual(action["views"], [[False, "form"]])
        ctx = action["context"]
        self.assertEqual(ctx["default_pet_id"], self.pet.id)
        self.assertEqual(ctx["default_partner_id"], self.owner.id)
        self.assertEqual(ctx["default_practitioner_id"], self.env.user.partner_id.id)
        visit = self.env["emr.encounter.veterinary"].with_context(**ctx).create({})
        self.assertEqual(visit.pet_id, self.pet)
        self.assertEqual(visit.partner_id, self.owner)
        self.assertEqual(visit.practitioner_id, self.env.user.partner_id)
        self.assertIn(visit.encounter_id, self.pet.encounter_ids)
        self.assertIn(visit, self.pet.consultation_ids)
        self.pet.deceased = True
        with self.assertRaises(UserError):
            self.pet.action_new_consultation()

    def test_new_prevention_preloads_the_pet(self):
        product = self.env["product.product"].create({
            "name": "Desparasitante",
            "type": "consu",
            "veterinary_kind": "medicine",
        })
        action = self.pet.action_new_prevention()
        self.assertEqual(action["context"]["default_pet_id"], self.pet.id)
        line = self.env["emr.pet.prevention"].with_context(**action["context"]).create({
            "kind": "deworming",
            "product_id": product.id,
            "date": fields.Date.context_today(self.pet),
            "next_date": fields.Date.add(fields.Date.context_today(self.pet), days=2),
        })
        self.assertEqual(line.pet_id, self.pet)
        self.assertIn(line, self.pet.prevention_ids)
        self.env["emr.pet.prevention"]._cron_send_reminders()
        self.assertTrue(line.activity_id)
        self.assertEqual(line.activity_id.res_id, self.pet.id)

    def test_visible_labels_are_spanish(self):
        self.assertEqual(self.env["emr.pet"]._fields["name"].string, "Nombre")
        self.assertEqual(self.env["emr.pet.weight"]._fields["date"].string, "Fecha")
        self.assertEqual(self.env["emr.pet"]._fields["deceased"].string, "Mascota fallecida")
        arch = self.env["emr.pet"].get_view()["arch"]
        self.assertIn('string="Fecha"', arch)
        self.assertIn('string="Estado"', arch)
        self.assertIn("Mascota fallecida", arch)
        self.assertNotIn('title="Fallecido"', arch)
        self.assertIn("Nueva aplicación", arch)
        self.assertIn('name="consultation_ids"', arch)
        self.assertNotIn("action_open_encounters", arch)
        self.assertNotIn("no_open", arch)
        self.assertFalse(self.env.ref(
            "emr_veterinary.menu_emr_veterinary_encounters", raise_if_not_found=False
        ))
        self.assertFalse(self.env.ref(
            "emr_veterinary.menu_emr_veterinary_prevention", raise_if_not_found=False
        ))
        self.assertTrue(self.env.ref("emr_veterinary.emr_encounter_veterinary_action"))
        self.assertTrue(self.env.ref("emr_veterinary.emr_pet_prevention_action"))
        for model_name in (
            "emr.pet.prevention",
            "emr.pet.weight",
            "emr.encounter",
            "emr.veterinary.prescription",
            "sale.order",
            "emr.appointment.book",
            "emr.appointment.charge",
        ):
            field = self.env[model_name]._fields["pet_id"]
            self.assertEqual(field.string, "Mascota", model_name)
        self.assertNotIn(">Date<", arch)
        self.assertNotIn('string="State"', arch)
        self.assertNotIn('string="Name"', arch)
        self.assertNotIn('string="Pet"', arch)

    def test_day_movements_list_consultations_and_sales_once(self):
        medicine = self.env["product.product"].create({
            "name": "Comprimido suelto",
            "type": "consu",
            "is_storable": True,
            "veterinary_kind": "medicine",
            "list_price": 500,
        })
        food = self.env["product.product"].create({
            "name": "Bolsa de alimento",
            "type": "consu",
            "is_storable": True,
            "veterinary_kind": "food",
            "list_price": 2000,
        })
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        self.env["stock.quant"]._update_available_quantity(
            medicine, warehouse.lot_stock_id, 10
        )
        self.env["stock.quant"]._update_available_quantity(
            food, warehouse.lot_stock_id, 10
        )
        Movement = self.env["emr.veterinary.movement"]
        visit = self._visit(self.pet, reason="Control")
        service_order = self.env["sale.order"].create({
            "partner_id": self.owner.id,
            "pet_id": self.pet.id,
            "is_appointment": True,
            "practitioner_id": self.vet.id,
            "order_line": [Command.create({
                "product_id": self.env.ref(
                    "emr_veterinary.product_consulta_veterinaria"
                ).id,
                "product_uom_qty": 1,
            })],
        })
        visit.order_id = service_order
        self.env.flush_all()
        service_only = Movement.search([
            ("res_model", "=", "sale.order"),
            ("res_id", "=", service_order.id),
        ])
        self.assertFalse(service_only)
        consulta = Movement.search([
            ("move_type", "=", "consulta"),
            ("res_id", "=", visit.id),
        ])
        self.assertEqual(len(consulta), 1)
        self.assertEqual(consulta.pet_id, self.pet)
        self.assertEqual(consulta.partner_id, self.owner)

        retail_order = self.env["sale.order"].create({
            "partner_id": self.owner.id,
            "pet_id": self.pet.id,
            "is_appointment": True,
            "practitioner_id": self.vet.id,
            "order_line": [
                Command.create({
                    "product_id": medicine.id,
                    "product_uom_qty": 2,
                }),
                Command.create({
                    "product_id": food.id,
                    "product_uom_qty": 1,
                }),
            ],
        })
        visit.order_id = retail_order
        self.env.flush_all()
        sales = Movement.search([
            ("res_model", "=", "sale.order"),
            ("res_id", "=", retail_order.id),
        ])
        self.assertEqual(len(sales), 1)
        self.assertEqual(sales.move_type, "venta")
        self.assertEqual(sales.partner_id, self.owner)
        self.assertEqual(sales.pet_id, self.pet)
        self.assertAlmostEqual(sales.amount_total, retail_order.amount_total)
        opened = sales.action_open_origin()
        self.assertEqual(opened["res_model"], "sale.order")
        self.assertEqual(opened["res_id"], retail_order.id)

        counter = self.env["sale.order"].create({
            "partner_id": self.owner.id,
            "is_appointment": False,
            "order_line": [Command.create({
                "product_id": food.id,
                "product_uom_qty": 1,
            })],
        })
        self.env.flush_all()
        counter_rows = Movement.search([
            ("res_model", "=", "sale.order"),
            ("res_id", "=", counter.id),
        ])
        self.assertEqual(len(counter_rows), 1)
        self.assertFalse(counter_rows.pet_id)

        action = self._call_new_sale_button([])
        self._assert_new_sale_action(action)
        action = self._call_new_sale_button(counter_rows.ids)
        self._assert_new_sale_action(action)
        self.assertEqual(
            self.env.ref("emr_veterinary.emr_veterinary_movement_action").context,
            "{'search_default_today': 1}",
        )

        counter.action_confirm()
        self.assertEqual(counter.state, "sale")
        self.assertTrue(counter.picking_ids)
        picking = counter.picking_ids
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        invoice = counter._create_invoices()
        self.assertEqual(invoice.partner_id, self.owner)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                food, warehouse.lot_stock_id
            ),
            9,
        )

    def test_deceased_field_is_on_the_pet_section(self):
        self.assertEqual(self.env["emr.pet"]._fields["deceased"].string, "Mascota fallecida")
        arch = self.env["emr.pet"].get_view()["arch"]
        root = etree.fromstring(arch.encode())
        owner = root.xpath("//group[@string='Dueño']")[0]
        pet = root.xpath("//group[@string='Mascota']")[0]
        self.assertFalse(owner.xpath(".//field[@name='deceased' or @name='deceased_date']"))
        self.assertEqual([node.get("name") for node in owner.xpath("./field")], ["owner_id"])
        names = [node.get("name") for node in pet.xpath("./field")]
        self.assertLess(names.index("neutered"), names.index("deceased"))
        self.assertLess(names.index("deceased"), names.index("deceased_date"))

    def _call_new_sale_button(self, ids):
        """Igual que ``/web/dataset/call_button``: el primer arg son los ids."""
        return call_kw(
            self.env["emr.veterinary.movement"],
            "action_new_sale",
            [ids],
            {},
        )

    def _assert_new_sale_action(self, action):
        self.assertEqual(action["res_model"], "sale.order")
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual(action["views"][0][1], "form")
        self.assertTrue(action["views"][0][0])
        self.assertFalse(action["context"]["default_is_appointment"])
        self.assertTrue(action["context"]["emr_veterinary_counter_sale"])

    def test_new_sale_header_button_accepts_web_client_ids(self):
        """Sin selección y con filas marcadas, Nuevo abre un sale.order."""
        self._assert_new_sale_action(self._call_new_sale_button([]))
        visit = self._visit(self.pet, reason="Control de botón")
        self.env.flush_all()
        row = self.env["emr.veterinary.movement"].search([
            ("move_type", "=", "consulta"),
            ("res_id", "=", visit.id),
        ])
        self.assertTrue(row)
        self._assert_new_sale_action(self._call_new_sale_button(row.ids))

    def _visit(self, pet, order=None, **extra):
        vals = {
            "pet_id": pet.id,
            "practitioner_id": self.vet.id,
            "encounter_type_id": self.encounter_type.id,
            "order_id": order.id if order else False,
        }
        vals.update(extra)
        return self.env["emr.encounter.veterinary"].create(vals)
