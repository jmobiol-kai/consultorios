##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class EmrAllergy(models.Model):
    """Nomenclador de alergias.

    El catálogo es común; el campo que lo usa lo declara cada tipo de historia
    clínica. Una alergia registrada en una atención es lo que se anotó ese día
    y se queda ahí: no se copia al paciente ni se sincroniza con él. Son
    momentos separados, y un registro clínico no se reinterpreta con datos
    posteriores.
    """

    _name = "emr.allergy"
    _description = "Alergia"
    _order = "name"

    name = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint(
        "UNIQUE (name)", "Ya hay una alergia con ese nombre."
    )
