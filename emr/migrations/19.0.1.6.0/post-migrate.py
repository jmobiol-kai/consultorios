##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""El mosaico de la aplicación pasa a llamarse Consultorio.

El nombre del menú raíz es traducible. Un -u escribe el término nuevo
en el idioma de la carga (en general en_US) y deja es_AR con el texto
viejo, «Historia clínica», si ya estaba guardado. Acá se pisa en todos
los idiomas instalados. El nombre técnico del módulo sigue siendo emr.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

LABEL = "Consultorio"


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    menu = env.ref("emr.menu_emr_root", raise_if_not_found=False)
    if not menu:
        return
    langs = [code for code, _name in env["res.lang"].get_installed()]
    langs.append(None)
    for code in langs:
        menu.with_context(lang=code).write({"name": LABEL})
    _logger.info("emr: el menú raíz quedó como %s.", LABEL)
