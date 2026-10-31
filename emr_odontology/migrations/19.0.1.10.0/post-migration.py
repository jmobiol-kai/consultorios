##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Prende «Pieza entera» en el catálogo que ya estaba cargado.

El xml de estados es noupdate, así que un -u no reescribe esas filas.
`post_init` tampoco corre en una actualización: solo al instalar. Esta
migración sí corre al pasar a 19.0.1.10.0. Es idempotente con el
`<function>` del xml: la primera de las dos deja la marca y la otra
no la vuelve a tocar.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    updated = env["emr.odontogram.condition"]._seed_whole_tooth()
    _logger.info(
        "emr_odontology: migración 19.0.1.10.0, pieza entera en %s estados.",
        updated,
    )
