##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class EmrPetColor(models.Model):
    """Color o pelaje, propio de cada especie. Igual que la raza."""

    _name = "emr.pet.color"
    _description = "Color de pelaje"
    _order = "species_id, name"

    name = fields.Char("Nombre", required=True)
    species_id = fields.Many2one(
        "emr.pet.species",
        string="Especie",
        required=True,
        ondelete="restrict",
        index=True,
    )
    active = fields.Boolean("Activo", default=True)

    _color_uniq = models.Constraint(
        "UNIQUE (species_id, name)",
        "Ese color ya está cargado para la especie.",
    )
