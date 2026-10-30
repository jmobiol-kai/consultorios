##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Las visitas que ya existían también llevan sus marcas al turno.

Antes de esta versión la marca del odontograma no tocaba el pedido. Se pasa
una vez por todas las consultas odontológicas, firmadas incluidas: la firma
congela la historia clínica, no lo que se cobra.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    visits = env["emr.encounter.odontology"].with_context(active_test=False).search([
        ("order_id", "!=", False),
    ])
    visits._sync_sale_order_lines()
    _logger.info(
        "emr_odontology: %s consultas sincronizadas con su turno.", len(visits)
    )
