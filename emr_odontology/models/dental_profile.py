##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Perfil odontológico: qué menús de emr no usa el consultorio dental.

No borra medicamentos, alergias ni la rendición. Con el perfil prendido
dejan de mostrarse en el menú. Otra especialidad lo apaga en Ajustes y
los vuelve a ver. El odontograma de Atención no está acá: ese menú se
oculta siempre, porque se abre desde el paciente.
"""

DENTAL_HIDDEN_MENU_XMLIDS = (
    "emr.menu_emr_medications",
    "emr.menu_emr_allergies",
    "emr.menu_emr_settlement",
)

DENTAL_PROFILE_PARAM = "emr_odontology.dental_profile"


def dental_profile_enabled(value):
    """El parámetro guarda el texto True o False. Vacío no es perfil dental."""
    return str(value).strip().lower() in {"1", "true", "yes"}
