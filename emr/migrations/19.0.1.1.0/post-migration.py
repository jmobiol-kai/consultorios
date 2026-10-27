##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""El estado del hueco pasó a ser calculado: hay que forzar el recálculo.

`emr.slot.state` existía como campo escrito a mano, con los valores `free`,
`taken` y `blocked`. Ahora es calculado desde el turno y absorbe sus etapas.

Odoo **no recalcula un campo almacenado que ya tiene valores**: al actualizar,
las filas viejas se quedan con `taken`, un valor que la selección nueva ni
siquiera tiene, y con eso la grilla muestra huecos sin estado y `available`
queda mal. Este script las pone al día una sola vez.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Slot = env["emr.slot"]
    slots = Slot.search([])
    if not slots:
        return

    for fname in ("state", "available"):
        env.add_to_compute(Slot._fields[fname], slots)
        slots.flush_recordset([fname])

    cr.execute("SELECT state, count(*) FROM emr_slot GROUP BY state ORDER BY 2 DESC")
    _logger.info(
        "emr: %s huecos recalculados. Estados: %s", len(slots), dict(cr.fetchall())
    )
