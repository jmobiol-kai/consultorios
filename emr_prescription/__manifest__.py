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
    "name": "EMR - Recetas",
    "version": "19.0.1.0.0",
    "category": "Services",
    "author": "filoquin",
    "license": "AGPL-3",
    "summary": "Pedido, autorización y entrega de recetas",
    "description": """
La receta con su propio flujo: un administrativo toma el pedido y lo relaciona
con un paciente, un profesional lo autoriza, y el paciente la retira.

No es un tipo de historia clínica —nadie atiende a nadie— pero **se lista con
las atenciones**, porque tiene que verse en la historia clínica del paciente
como un ítem más. Eso se resuelve con la delegación en `emr.encounter`, que es
la lista unificada: la receta tiene su fila ahí sin dejar de ser otra cosa.

El flujo entra en los estados que la atención ya tiene, sin agregar ninguno:
el pedido es `draft`, la autorización cierra y firma. La entrega no es un
estado: no cambia lo que la receta dice.

Emitir recetas no es propio de ninguna instalación en particular, así que esto
es un módulo de familia y no de cliente.
    """,
    "depends": [
        "emr",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/emr_prescription_security.xml",
        "views/emr_prescription_views.xml",
        "data/emr_encounter_type_data.xml",
        "data/ir_sequence_data.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
