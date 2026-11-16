##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Los pacientes quedan con tipo de documento DNI.

En las bases ya cargadas hay pacientes con CUIT u otro tipo. El
documento de un paciente es siempre DNI. Si la localización argentina
no está instalada, no hay tipo que asignar y no se toca nada.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Partner = env["res.partner"]
    if "l10n_latam_identification_type_id" not in Partner._fields:
        _logger.info("emr: no hay tipo de documento latinoamericano; no se migra el DNI.")
        return
    dni = env.ref("l10n_ar.it_dni", raise_if_not_found=False)
    if not dni:
        _logger.info("emr: l10n_ar.it_dni no está; no se migra el DNI.")
        return
    patients = Partner.with_context(active_test=False).search([
        ("is_patient", "=", True),
        ("l10n_latam_identification_type_id", "!=", dni.id),
    ])
    if not patients:
        return
    patients.write({"l10n_latam_identification_type_id": dni.id})
    _logger.info("emr: %s pacientes pasaron a DNI.", len(patients))
