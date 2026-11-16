##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""El menú Personas pasa a llamarse Contactos.

Ahí también están las obras sociales. El nombre es traducible: un -u
escribe el término nuevo en el idioma de la carga y puede dejar es_AR
con «Personas». Se pisa en todos los idiomas instalados. Los submenús
no se tocan.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

LABEL = "Contactos"


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    menu = env.ref("emr.menu_emr_people", raise_if_not_found=False)
    if not menu:
        return
    langs = [code for code, _name in env["res.lang"].get_installed()]
    langs.append(None)
    for code in langs:
        menu.with_context(lang=code).write({"name": LABEL})
    _logger.info("emr: el menú de contactos quedó como %s.", LABEL)
