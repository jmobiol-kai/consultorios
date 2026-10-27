##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class EmrDiagnosis(models.Model):
    """Nomenclador de diagnósticos.

    Es un modelo y no una etiqueta porque se usa para filtrar y reportar.
    """

    _name = "emr.diagnosis"
    _description = "Diagnóstico"
    _order = "name"
    _parent_store = True

    name = fields.Char(required=True, index=True)
    code = fields.Char(index=True)
    parent_id = fields.Many2one("emr.diagnosis", ondelete="restrict", index=True)
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many("emr.diagnosis", "parent_id")
    active = fields.Boolean(default=True)
