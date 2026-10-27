##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class EmrEncounterType(models.Model):
    """Los tipos de historia clínica que esta instalación tiene habilitados.

    Cada tipo es un modelo propio (herencia por delegación sobre emr.encounter).
    Este registro es lo que permite que cada clínica declare los suyos sin
    tocar el resto.
    """

    _name = "emr.encounter.type"
    _description = "Tipo de historia clínica"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    model_name = fields.Char(
        "Modelo",
        required=True,
        help="Nombre técnico del modelo que implementa este tipo, "
        "por ejemplo emr.encounter.consultation.",
    )
    summary_template = fields.Char(
        "Plantilla del resumen",
        help="Identificador de la plantilla QWeb que dibuja este tipo en el "
        "panel de historia del paciente, por ejemplo "
        "emr.encounter_summary_consultation. Vacío usa el resumen genérico.",
    )
    report_template = fields.Char(
        "Plantilla del informe",
        help="Identificador de la plantilla QWeb que dibuja el cuerpo clínico "
        "de este tipo en los informes impresos, por ejemplo "
        "emr.report_encounter_consultation_body. La usan tanto el informe "
        "individual como la historia clínica completa del paciente. Vacío "
        "cae al volcado genérico de campos.",
    )
    active = fields.Boolean(default=True)

    _model_uniq = models.Constraint(
        "UNIQUE (model_name)", "Ya hay un tipo para ese modelo."
    )
