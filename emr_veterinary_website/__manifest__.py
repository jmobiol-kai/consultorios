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
    "name": "Sitio de la veterinaria",
    "version": "19.0.1.1.3",
    "category": "Website",
    "author": "filoquin",
    "license": "AGPL-3",
    "summary": "Turnos online sin cuenta y tienda con pago al retirar",
    "description": """
Sitio público de la clínica veterinaria.

/turnos toma un turno sin cuenta de cliente: elige profesional y práctica
si quiere, un hueco libre de la agenda, y carga dueño y mascota. Si el
correo o el teléfono ya existen, reutiliza el contacto. La mascota se
busca por nombre y especie de ese dueño.

La tienda es website_sale. Publicá los productos de venta libre
(medicamento, accesorio o alimento) para que aparezcan. El pago es al
retirar en la clínica: método «Pagar al retirar» y envío «Retiro en la
clínica», sin pasarela online. Esos pedidos entran en Movimientos del día.
    """,
    "depends": [
        "emr_veterinary",
        "website",
        "website_sale",
        "payment_custom",
        "delivery",
    ],
    "data": [
        "data/pay_on_pickup.xml",
        "data/mail_template.xml",
        "views/turnos_templates.xml",
        "views/website_menus.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "emr_veterinary_website/static/src/scss/turnos.scss",
            "emr_veterinary_website/static/src/js/turnos.js",
        ],
        "web.assets_tests": [
            "emr_veterinary_website/static/tests/tours/turnos_month.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
}
