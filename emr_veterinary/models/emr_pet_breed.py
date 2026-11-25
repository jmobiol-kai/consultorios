##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class EmrPetBreed(models.Model):
    _name = "emr.pet.breed"
    _description = "Raza"
    _order = "species_id, name"

    name = fields.Char(required=True)
    species_id = fields.Many2one(
        "emr.pet.species", string="Especie", required=True, ondelete="restrict", index=True
    )
    active = fields.Boolean(default=True)

    _breed_uniq = models.Constraint(
        "UNIQUE (species_id, name)",
        "Esa raza ya está cargada para la especie.",
    )
