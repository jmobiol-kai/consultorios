##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Qué profesional preseleccionar en Atender ahora, y dónde se guarda.

No importa Odoo: el asistente hace las búsquedas y este módulo decide.
Así se puede probar la regla sin levantar el servidor.
"""

# Una clave de ir.config_parameter por usuario de Odoo. El valor es el
# id del último profesional que ese usuario confirmó en el asistente.
PARAM_PREFIX = "emr_odontology.walkin_last_practitioner"


def walkin_practitioner_param_key(user_id):
    """Clave del recuerdo. Dos usuarios no comparten la elección."""
    return "%s.%s" % (PARAM_PREFIX, int(user_id))


def parse_stored_practitioner_id(raw):
    """Id guardado, o False si no hay valor o no es un id."""
    if raw is None or raw is False:
        return False
    text = str(raw).strip()
    if not text or not text.isdigit():
        return False
    return int(text) or False


def choose_walkin_practitioner(
    available_count, sole_id=None, remembered_id=None, remembered_allowed=False
):
    """Id a preseleccionar, o False para dejar el campo vacío.

    Un solo profesional en el dominio (la lista que el campo deja elegir)
    gana siempre, también la primera vez y aunque haya un recuerdo viejo.
    Con varios, se usa el último que este usuario confirmó, si sigue en
    esa lista. Si no hay recuerdo, o el guardado ya no se puede elegir,
    el campo queda vacío.
    """
    if available_count == 1 and sole_id:
        return sole_id
    if available_count > 1 and remembered_allowed and remembered_id:
        return remembered_id
    return False
