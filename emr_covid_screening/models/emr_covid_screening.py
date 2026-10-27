##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""El triage de la pandemia, como archivo histórico.

Los campos copian los del sistema viejo, incluidas las tres rondas: el mismo
cuestionario se repetía hasta tres veces antes del estudio. Podría modelarse
más prolijo —una cabecera y tres líneas— pero es un archivo muerto y la
fidelidad vale más: que cada campo se llame como se llamaba permite verificar
un dato contra el sistema viejo sin traducir nada.

Todo entra como texto porque así estaba: las respuestas eran libres, no
booleanos. "no", "No", "niega", "sin datos" conviven en la misma columna, y
normalizarlas ahora sería inventar una precisión que el dato no tiene.
"""
from odoo import fields, models


class EmrCovidScreening(models.Model):
    _name = "emr.encounter.covid.screening"
    _description = "Triage COVID (histórico)"
    _inherit = "emr.encounter.mixin"
    _inherits = {"emr.encounter": "encounter_id"}

    # ------------------------------------------------------------------
    # Contexto del cuestionario
    # ------------------------------------------------------------------
    study_requested = fields.Char("Endoscopía solicitada")
    days_10_before = fields.Text("A 10 días del procedimiento")
    days_7_before = fields.Text("A 7 días del procedimiento")

    # ------------------------------------------------------------------
    # Las tres rondas
    #
    # Cada una tiene su fecha, quién la hizo y las mismas nueve preguntas.
    # Se repiten los campos en vez de normalizarlos porque así vienen, y
    # porque una ronda que no se hizo tiene que quedar vacía y no ausente.
    # ------------------------------------------------------------------
    date_1 = fields.Date("Fecha (1ª)")
    done_by_1 = fields.Char("Realizado por (1ª)")
    fever_1 = fields.Char("Fiebre (1ª)")
    cough_1 = fields.Char("Tos (1ª)")
    sore_throat_1 = fields.Char("Dolor de garganta (1ª)")
    odynophagia_1 = fields.Char("Odinofagia (1ª)")
    breathlessness_1 = fields.Char("Falta de aire (1ª)")
    headache_1 = fields.Char("Cefalea (1ª)")
    abdominal_pain_1 = fields.Char("Dolor abdominal (1ª)")
    smell_loss_1 = fields.Char("Pérdida del olfato (1ª)")
    taste_loss_1 = fields.Char("Pérdida del gusto (1ª)")
    contact_1 = fields.Char("Contacto con paciente COVID (1ª)")
    travel_1 = fields.Char("Antecedente de viajes (1ª)")
    other_1 = fields.Text("Otros (1ª)")

    date_2 = fields.Date("Fecha (2ª)")
    done_by_2 = fields.Char("Realizado por (2ª)")
    fever_2 = fields.Char("Fiebre (2ª)")
    cough_2 = fields.Char("Tos (2ª)")
    sore_throat_2 = fields.Char("Dolor de garganta (2ª)")
    odynophagia_2 = fields.Char("Odinofagia (2ª)")
    breathlessness_2 = fields.Char("Falta de aire (2ª)")
    headache_2 = fields.Char("Cefalea (2ª)")
    abdominal_pain_2 = fields.Char("Dolor abdominal (2ª)")
    smell_loss_2 = fields.Char("Pérdida del olfato (2ª)")
    taste_loss_2 = fields.Char("Pérdida del gusto (2ª)")
    contact_2 = fields.Char("Contacto con paciente COVID (2ª)")
    travel_2 = fields.Char("Antecedente de viajes (2ª)")
    other_2 = fields.Char("Otros (2ª)")

    date_3 = fields.Date("Fecha (3ª)")
    fever_3 = fields.Char("Fiebre (3ª)")
    cough_3 = fields.Char("Tos (3ª)")
    sore_throat_3 = fields.Char("Dolor de garganta (3ª)")
    odynophagia_3 = fields.Char("Odinofagia (3ª)")
    breathlessness_3 = fields.Char("Falta de aire (3ª)")
    headache_3 = fields.Char("Cefalea (3ª)")
    abdominal_pain_3 = fields.Char("Dolor abdominal (3ª)")
    smell_loss_3 = fields.Char("Pérdida del olfato (3ª)")
    taste_loss_3 = fields.Char("Pérdida del gusto (3ª)")
    contact_3 = fields.Char("Contacto con paciente COVID (3ª)")
    travel_3 = fields.Char("Antecedente de viajes (3ª)")
    other_3 = fields.Char("Otros (3ª)")
