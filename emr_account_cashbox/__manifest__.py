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
    "name": "EMR - Caja",
    "version": "19.0.1.0.0",
    "category": "Services",
    "author": "filoquin",
    "license": "AGPL-3",
    "summary": "Operar la caja desde la aplicación de historia clínica",
    "description": """
Puente entre el EMR y las cajas de Adhoc.

El EMR no necesita cajas para funcionar: cobra emitiendo un pago, y si hay una
sesión de caja abierta el pago se engancha solo, porque `cashbox_session_id` es
un campo calculado de `account_cashbox`.

Lo que este módulo agrega es el otro lado: que quien atiende el mostrador pueda
ver su caja y sus movimientos sin salir de la aplicación, y hacer la rendición.

Se instala solo cuando el EMR y las cajas conviven.
    """,
    "depends": [
        "emr",
        "account_cashbox",
    ],
    "data": [
        "views/emr_cashbox_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "application": False,
}
