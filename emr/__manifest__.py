##############################################################################
#
#    Copyright (C) 2026  filoquin
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name": "EMR - Turnos e Historia Clínica",
    "version": "19.0.1.1.0",
    "category": "Services",
    "author": "filoquin",
    "license": "AGPL-3",
    "summary": "Agenda, turnos, historia clínica y cobro para centros de salud",
    "depends": [
        "base",
        "resource",
        "sale_management",
        "account",
        "partner_contact_birthdate",
    ],
    "data": [
        "security/emr_security.xml",
        "security/ir.model.access.csv",
        # Configuración
        "views/emr_location_views.xml",
        "views/emr_specialty_views.xml",
        "views/emr_diagnosis_views.xml",
        "views/emr_medication_views.xml",
        "views/emr_allergy_views.xml",
        "views/emr_practice_type_views.xml",
        # Los asistentes primero: sus acciones se referencian desde los
        # botones de las demás vistas, y una acción tiene que existir antes
        # de que alguien la nombre.
        "views/emr_slot_generate_views.xml",
        "views/emr_slot_filter_views.xml",
        "views/emr_demand_book_views.xml",
        "views/emr_appointment_book_views.xml",
        "views/emr_appointment_addon_views.xml",
        "views/emr_appointment_charge_views.xml",
        "views/emr_encounter_retype_views.xml",
        "views/emr_settlement_views.xml",
        # Vistas
        "views/emr_encounter_templates.xml",
        "views/res_partner_views.xml",
        "views/resource_calendar_views.xml",
        "views/product_template_views.xml",
        "views/emr_slot_views.xml",
        "views/sale_order_views.xml",
        "views/account_payment_views.xml",
        "views/emr_encounter_form_base.xml",
        "views/emr_encounter_views.xml",
        "views/emr_menus.xml",
        # Después de los menús: cuelga de menu_emr_config, y un menú tiene
        # que existir antes de que alguien se le cuelgue.
        "views/sale_order_template_views.xml",
        "report/emr_encounter_report_base.xml",
        "report/emr_patient_history_report.xml",
        # Datos
        "data/emr_data.xml",
        "data/ir_cron.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "emr/static/src/patient_history/*.js",
            "emr/static/src/patient_history/*.xml",
            "emr/static/src/patient_history/*.scss",
        ],
    },
    "demo": [
        "demo/emr_demo.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
}
