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
    "name": "EMR - Avisos por WhatsApp",
    "version": "19.0.1.0.0",
    "category": "Services",
    "author": "filoquin",
    "license": "AGPL-3",
    "summary": "Confirmación y recordatorio de turnos por WhatsApp",
    "description": """
Avisa al paciente por WhatsApp cuando se le asigna un turno, y le recuerda
antes de la hora.

**Nada se envía en el momento.** Asignar un turno lo deja encolado y un cron
lo manda unos minutos después. Eso da tiempo a corregir o cancelar antes de
que el paciente reciba algo, que es lo que pasa de verdad en un mostrador: se
asigna, se descubre que era otro día, se corrige. Un aviso ya enviado no se
puede desenviar.

De paso, sacar el envío de la transacción del turno lo hace inofensivo: si
WhatsApp está caído o la plantilla no está aprobada, el turno se asigna igual.

Requiere el módulo `whatsapp` de Enterprise y una cuenta de WhatsApp Business
API. **Las plantillas las aprueba Meta**, no Odoo: este módulo las trae en
borrador y alguien tiene que subirlas y esperar la aprobación antes de que
salga el primer mensaje.
    """,
    "depends": [
        "emr",
        "whatsapp",
    ],
    "data": [
        "data/whatsapp_template_data.xml",
        "data/ir_cron_data.xml",
        "views/sale_order_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
