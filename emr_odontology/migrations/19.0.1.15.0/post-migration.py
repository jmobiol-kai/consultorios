##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Saca el asistente de Atender ahora.

La pantalla previa (paciente y profesional) ya no existe. El modelo
transitorio se borra acá por si el reflejo del registro no lo alcanza
en esta actualización: era un transient, no guarda historia clínica.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    model = env["ir.model"].search([("model", "=", "emr.odontology.walkin")])
    if model:
        # state='base': sin _force_unlink Odoo no deja borrar un modelo del
        # módulo. El modelo ya no está en el registro, así que la tabla no
        # se dropea sola.
        model.with_context(_force_unlink=True).unlink()
    cr.execute("DROP TABLE IF EXISTS emr_odontology_walkin CASCADE")
    _logger.info("emr_odontology: se eliminó el asistente emr.odontology.walkin.")
