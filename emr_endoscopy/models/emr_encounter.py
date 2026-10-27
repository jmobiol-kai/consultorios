##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Los tipos de historia clínica de endoscopía digestiva.

Cada uno es un modelo propio con sus campos, que delega los comunes en
emr.encounter. Están acá y no en emr porque no toda instalación hace
endoscopías: una clínica que solo atiende consultorio instala emr y no ve
ninguno de estos tres.

Lo que NO se hace es un modelo único con todos los campos mostrados u ocultos
según el tipo: termina en una tabla de cientos de columnas casi siempre nulas.
"""
from odoo import fields, models


class EmrEncounterColonoscopy(models.Model):
    _name = "emr.encounter.colonoscopy"
    _description = "Colonoscopía"
    _inherit = "emr.encounter.mixin"
    _inherits = {"emr.encounter": "encounter_id"}

    referring_practitioner_id = fields.Many2one(
        "res.partner",
        string="Médico que la solicita",
        domain=lambda self: [
            ("category_id", "=", self.env.ref("emr.partner_category_medico").id)
        ],
        help="Quien derivó el estudio. Es un contacto del padrón, no alguien "
        "que atienda acá: por eso filtra por la etiqueta y no por "
        "`is_practitioner`.",
    )
    anesthetist_id = fields.Many2one(
        "res.partner",
        string="Anestesista",
        domain=lambda self: [
            ("category_id", "=",
             self.env.ref("emr.partner_category_anestesista").id)
        ],
    )
    equipment = fields.Char("Equipo utilizado")
    study_reason = fields.Char("Motivo del estudio")

    inspection = fields.Text("Inspección")
    rectal_exam = fields.Text("Tacto rectal")
    anoscopy = fields.Text("Anoscopía")
    endoscopy = fields.Text("Endoscopía")
    ileal_intubation = fields.Char("Intubación ileal")
    procedures = fields.Char("Procedimientos")
    complete = fields.Boolean("Completa")
    sample_sent = fields.Boolean("Muestra enviada")
    conclusions = fields.Text("Conclusiones")
    anesthesia_report = fields.Text("Informe del anestesista")


class EmrEncounterUpperEndoscopy(models.Model):
    _name = "emr.encounter.upper.endoscopy"
    _description = "Endoscopía alta"
    _inherit = "emr.encounter.mixin"
    _inherits = {"emr.encounter": "encounter_id"}

    referring_practitioner_id = fields.Many2one(
        "res.partner",
        string="Médico que la solicita",
        domain=lambda self: [
            ("category_id", "=", self.env.ref("emr.partner_category_medico").id)
        ],
    )
    anesthetist_id = fields.Many2one(
        "res.partner",
        string="Anestesista",
        domain=lambda self: [
            ("category_id", "=",
             self.env.ref("emr.partner_category_anestesista").id)
        ],
    )
    equipment = fields.Char("Equipo utilizado")
    study_reason = fields.Char("Motivo del estudio")

    esophagus = fields.Text("Esófago")
    stomach = fields.Text("Estómago")
    duodenum = fields.Text("Duodeno")
    conclusions = fields.Text("Conclusiones")
    anesthesia_report = fields.Text("Informe del anestesista")


class EmrEncounterBanding(models.Model):
    _name = "emr.encounter.banding"
    _description = "Banding"
    _inherit = "emr.encounter.mixin"
    _inherits = {"emr.encounter": "encounter_id"}

    referring_practitioner_id = fields.Many2one(
        "res.partner",
        string="Médico que la solicita",
        domain=lambda self: [
            ("category_id", "=", self.env.ref("emr.partner_category_medico").id)
        ],
    )
    body = fields.Html("Relato")
