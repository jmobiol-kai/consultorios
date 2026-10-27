##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class EmrMedication(models.Model):
    """Vademécum: la medicación que se puede indicar o prescribir.

    Es un modelo y no una etiqueta por la misma razón que emr.diagnosis: se
    usa para filtrar y reportar, y una etiqueta no sostiene eso.

    Lo que NO es: el historial de lo que alguien tipeó. En el sistema que se
    reemplaza había dos vocabularios para esto — un vademécum cargado de 8.985
    entradas y otro de 21.490 que el formulario engordaba solo, creando el
    término cada vez que se escribía algo que no existía. Los dos tenían apenas
    160 nombres en común. Acá entra el catálogo; el texto que se escribió a
    mano queda en el renglón que lo usó.
    """

    _name = "emr.medication"
    _description = "Medicamento"
    _order = "name"

    name = fields.Char(required=True, index=True)
    code = fields.Char(index=True, help="Código del nomenclador, si tiene.")
    active_ingredient = fields.Char("Droga")
    presentation = fields.Char("Presentación")
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint(
        "UNIQUE (name)", "Ya hay un medicamento con ese nombre."
    )
