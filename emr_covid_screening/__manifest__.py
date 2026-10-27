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
    "name": "EMR - Triage COVID (histórico)",
    "version": "19.0.1.0.0",
    "category": "Services",
    "author": "filoquin",
    "license": "AGPL-3",
    "summary": "El cuestionario de screening de la pandemia, como archivo",
    "description": """
Un tipo de historia clínica más: el triage que se hacía antes de un estudio
durante la pandemia.

**No es un módulo para usar, es un archivo.** Existe para que los 18.368
cuestionarios que la clínica cargó entre 2020 y 2023 sigan estando y se puedan
consultar. Nadie va a cargar uno nuevo.

Por eso el modelo copia los campos de origen tal cual, con sus tres rondas y
todo: en un archivo histórico, la fidelidad vale más que la prolijidad. Que un
campo se llame como se llamaba permite verificar el dato contra el sistema
viejo sin traducir nada.
    """,
    "depends": [
        "emr",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/emr_covid_screening_templates.xml",
        "views/emr_covid_screening_views.xml",
        "data/emr_encounter_type_data.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
