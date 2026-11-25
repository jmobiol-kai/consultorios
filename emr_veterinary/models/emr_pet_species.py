##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class EmrPetSpecies(models.Model):
    _name = "emr.pet.species"
    _description = "Especie"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint(
        "UNIQUE (name)",
        "Ya existe esa especie.",
    )
