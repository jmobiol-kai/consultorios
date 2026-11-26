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
    "name": "Veterinaria",
    "version": "19.0.1.5.0",
    "category": "Services",
    "author": "filoquin",
    "license": "AGPL-3",
    "summary": "Mascotas, historia clínica, vacunas y stock para la clínica veterinaria",
    "description": """
Clínica veterinaria sobre el consultorio (emr).

El paciente es la mascota. El dueño es un contacto (res.partner): es quien
paga, no un paciente clínico y no hace falta marcarlo como tal. No usa obra
social, afiliado ni arancel del financiador.

La consulta es un tipo de historia clínica (emr.encounter.veterinary) con los
mismos estados: en elaboración, cerrada y firmada. Firmada no se edita.
El panel de historia y el PDF quedan en la ficha de la mascota.
    """,
    "depends": [
        "emr",
        "stock",
        "sale_stock",
        "product_expiry",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/emr_veterinary_security.xml",
        "data/emr_veterinary_data.xml",
        "data/emr_pet_breed_data.xml",
        "data/emr_pet_color_data.xml",
        "data/ir_cron.xml",
        "data/emr_veterinary_auto_delivery.xml",
        "views/emr_pet_species_views.xml",
        "views/emr_pet_breed_views.xml",
        "views/emr_pet_color_views.xml",
        "views/emr_pet_views.xml",
        "views/emr_encounter_templates.xml",
        "views/emr_encounter_views.xml",
        "views/emr_prevention_views.xml",
        "views/emr_prescription_views.xml",
        "views/product_template_views.xml",
        "views/sale_order_views.xml",
        "views/emr_appointment_book_views.xml",
        "views/emr_appointment_charge_views.xml",
        "views/emr_veterinary_movement_views.xml",
        "report/emr_encounter_reports.xml",
        "report/emr_prescription_report.xml",
        "report/emr_pet_history_report.xml",
        "views/emr_menus.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "emr_veterinary/static/src/patient_history/patient_history.js",
            "emr_veterinary/static/src/appointment_calendar/appointment_calendar.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": True,
}
