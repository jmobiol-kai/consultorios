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
    "name": "EMR - Odontología",
    "version": "19.0.1.10.0",
    "category": "Services",
    "author": "filoquin",
    "license": "AGPL-3",
    "summary": "Odontograma del paciente y consulta odontológica",
    "description": """
Agrega la consulta odontológica como tipo de historia clínica, y el
odontograma: uno por paciente, con el estado actual de cada pieza.

La visita delega en `emr.encounter`, igual que la endoscopía. Lo que se
anota en la visita —pieza, cara, condición y estado— se vuelca al
odontograma. El historial queda en las atenciones; el odontograma es la
boca como está ahora.

Cada marca que es una práctica (condición distinta de sano/ausente, en
estado "A tratar" o "Tratado") agrega una línea al turno de la atención,
con el producto de servicio de su condición y una descripción como
"Caries distal pieza 14 (A tratar)".

Atender ahora: para el paciente que llega sin turno. Desde el menú
Atención, la ficha del paciente o su odontograma, crea el turno (con el
hueco de demanda si el profesional tiene franja abierta) y abre la consulta
odontológica en atención, sin pasar por el cobro. Lo que se marca en la
consulta pasa solo al presupuesto, que se abre con "Ver presupuesto".
Las correcciones hechas directo en el odontograma no se cobran.

En la consulta, la historia clínica sigue al costado del formulario.
Esa columna es más angosta que el panel habitual (cerca de un 30%
menos) y el odontograma se dibuja un 25% más chico, para que el mapa
y la historia quepan en la misma fila.

La cabecera de la consulta es más compacta. Paciente queda a la
izquierda. Turno está en la mitad derecha, unos 5 cm antes del borde,
y la fecha de atención va en esa misma fila, a la derecha del turno.
Profesional va en la fila de la locación. Motivo y evolución ocupan
menos alto,
y no se muestra el aviso azul sobre el odontograma. La leyenda de
condiciones (sano, caries, obturación, …) es más grande.

En el mapa el primer clic selecciona la cara y el segundo la deja
en blanco, sin recorrer colores. El color (sano, caries, corona, …)
se elige después, en la leyenda. Si el estado es de la pieza entera,
ese color pinta todas las caras: corona, implante, prótesis, ausente,
sano y extracción indicada vienen así. Caries, obturación y el resto
pintan solo la cara elegida. Una marca de la pieza se sigue viendo en
las caras que no tienen marca propia.
En Configuración, Estados deja cambiar el nombre, el color y si el
estado es de la pieza entera. El código técnico no se toca, así las
marcas ya guardadas siguen pintando.

En Configuración, Estados de la marca deja cambiar el nombre de la
columna Estado (Presente, A tratar, Tratado, Ausente, No erupcionado).
El código técnico no se toca. Al presupuesto siguen yendo pending y
treated, aunque el nombre visible sea otro. Al elegir una condición
en la leyenda, el estado inicial sigue siendo el de ese código
(caries queda pending).

La notación es FDI. Las piezas temporarias están en el mismo esquema y se
muestran aparte en el mapa.
    """,
    "depends": [
        "emr",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/emr_odontology_security.xml",
        "views/emr_encounter_templates.xml",
        "views/emr_odontogram_views.xml",
        "views/emr_encounter_views.xml",
        "views/res_partner_views.xml",
        "views/product_template_views.xml",
        "report/emr_encounter_reports.xml",
        "data/emr_odontogram_condition_data.xml",
        "data/emr_odontogram_status_data.xml",
        "data/emr_odontology_data.xml",
        "data/emr_odontology_sale_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "emr_odontology/static/src/odontogram/odontogram_chart_logic.js",
            "emr_odontology/static/src/odontogram/odontogram_chart.js",
            "emr_odontology/static/src/odontogram/odontogram_chart.xml",
            "emr_odontology/static/src/odontogram/odontogram_chart.scss",
            "emr_odontology/static/src/encounter_form.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
}
