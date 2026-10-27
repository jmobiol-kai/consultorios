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
    "name": "EMR - Endoscopía",
    "version": "19.0.1.0.0",
    "category": "Services",
    "author": "filoquin",
    "license": "AGPL-3",
    "summary": "Historias clínicas de endoscopía digestiva",
    "description": """
Agrega tres tipos de historia clínica: colonoscopía, endoscopía alta y banding.

Cada tipo es un modelo propio que delega en `emr.encounter`, con su formulario
y su plantilla de resumen. Instalarlo o no cambia qué puede registrar la
clínica, sin tocar nada de lo que ya está.

Es el patrón previsto por el diseño: el conjunto de tipos varía según la
instalación, y un tipo nuevo llega como un módulo y no como una columna más en
una tabla que ya tiene demasiadas.
    """,
    "depends": [
        "emr",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/emr_encounter_templates.xml",
        "views/emr_encounter_views.xml",
        "report/emr_encounter_reports.xml",
        "data/emr_encounter_type_data.xml",
    ],
    "demo": [
        "demo/emr_endoscopy_demo.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
