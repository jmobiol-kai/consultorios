##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class EmrSpecialty(models.Model):
    _name = "emr.specialty"
    _description = "Especialidad médica"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char()
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint(
        "UNIQUE (name)", "Ya existe una especialidad con ese nombre."
    )
