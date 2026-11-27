##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Si el texto viejo coincide con un color de la especie, queda el catálogo.
Si no, se conserva en color anotado.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    if "color_note" not in env["emr.pet"]._fields:
        return
    env["emr.pet"]._match_legacy_colors()
