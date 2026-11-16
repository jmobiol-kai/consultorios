##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Qué historia abre un turno cuando el consultorio es odontológico.

No importa Odoo: el modelo solo elige el nombre técnico.
"""

GENERIC_CONSULTATION_MODEL = "emr.encounter.consultation"
ODONTOLOGY_ENCOUNTER_MODEL = "emr.encounter.odontology"


def preferred_encounter_model(product_model, dental_profile, dental_available=True):
    """Modelo de la visita que corresponde a este turno.

    Con el perfil odontológico, la consulta genérica («Consulta de
    consultorio») abre el odontograma. Una práctica que ya nombra otra
    especialidad —endoscopía, por ejemplo— no se cambia.
    """
    model = product_model or ""
    if (
        dental_profile
        and dental_available
        and model in ("", GENERIC_CONSULTATION_MODEL)
    ):
        return ODONTOLOGY_ENCOUNTER_MODEL
    return model
