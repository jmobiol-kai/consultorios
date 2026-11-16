##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Qué se fija y qué se esconde en la ficha de un paciente.

No importa Odoo. El tipo de documento DNI solo se propone si el dato
existe: sin localización argentina no hay nada que poner.
"""

DNI_XMLID = "l10n_ar.it_dni"


def patient_identity_defaults(is_patient, dni_type_id, has_identification_field):
    """Valores de un paciente: siempre persona, y DNI si el tipo existe.

    Sin el tilde de paciente no se toca nada, para no cambiar una obra
    social ni un contacto común.
    """
    if not is_patient:
        return {}
    vals = {
        "is_company": False,
        "company_type": "person",
    }
    if has_identification_field and dni_type_id:
        vals["l10n_latam_identification_type_id"] = dni_type_id
    return vals


def merge_invisible(current, extra="is_patient"):
    """Suma `extra` a un invisible que ya tenía la vista."""
    current = (current or "").strip()
    if not current:
        return extra
    if current == extra:
        return current
    return "(%s) or %s" % (current, extra)
