##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""La consulta de consultorio, el tipo de historia clínica que trae el núcleo.

Es un modelo propio con sus campos, que delega los comunes en emr.encounter.
Los tipos que no toda instalación usa viven en su propio módulo — la
endoscopía digestiva, por ejemplo, está en emr_endoscopy.

Lo que NO se hace es un modelo único con todos los campos mostrados u ocultos
según el tipo: termina en una tabla de cientos de columnas casi siempre nulas.
"""
from odoo import api, fields, models


class EmrEncounterConsultation(models.Model):
    """Consulta de consultorio. Es el tipo más frecuente."""

    _name = "emr.encounter.consultation"
    _description = "Historia clínica de consultorio"
    _inherit = "emr.encounter.mixin"
    _inherits = {"emr.encounter": "encounter_id"}

    weight = fields.Float("Peso (kg)")
    height = fields.Float("Talla (cm)")
    bmi = fields.Float("IMC", compute="_compute_bmi", store=True)
    blood_pressure_max = fields.Integer("Presión máxima")
    blood_pressure_min = fields.Integer("Presión mínima")

    reason = fields.Text("Motivo de consulta")
    notes = fields.Text("Evolución")
    lab_line_ids = fields.One2many(
        "emr.encounter.lab.line", "consultation_id", string="Análisis"
    )

    @api.depends("weight", "height")
    def _compute_bmi(self):
        for rec in self:
            if rec.weight and rec.height:
                meters = rec.height / 100.0
                rec.bmi = rec.weight / (meters * meters)
            else:
                rec.bmi = 0.0


class EmrEncounterLabLine(models.Model):
    """Un análisis con su valor y su unidad.

    El valor va numérico, con un campo de texto aparte para lo que no es un
    número. En el sistema que reemplaza era un varchar de diez caracteres, así
    que cualquier cálculo tenía que castear y tolerar basura.
    """

    _name = "emr.encounter.lab.line"
    _description = "Análisis de la historia clínica"
    _order = "date desc, id"

    consultation_id = fields.Many2one(
        "emr.encounter.consultation", required=True, ondelete="cascade", index=True
    )
    name = fields.Char("Análisis", required=True)
    value = fields.Float("Valor")
    value_text = fields.Char(
        "Valor no numérico", help="Para resultados como 'no reactivo' o '< 0,5'."
    )
    uom_name = fields.Char("Unidad")
    date = fields.Date("Fecha", default=fields.Date.context_today)
