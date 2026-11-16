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


def patient_ids_to_switch_to_dni(patients, dni_type_id):
    """Pacientes cuyo tipo de documento no es DNI.

    `patients` es una lista de `(id, tipo_actual)`. Sin tipo DNI no hay
    nada que migrar.
    """
    if not dni_type_id:
        return []
    return [partner_id for partner_id, current in patients if current != dni_type_id]


# Pestañas que un paciente no usa. El nombre es el técnico, así no depende
# de la traducción. followup_tab lo agrega om_account_followup; si el
# módulo no está, la pestaña no existe y no se toca.
PATIENT_HIDDEN_PAGE_NAMES = frozenset({
    "accounting",
    "accounting_disabled",
    "followup_tab",
    "internal_notes",
    "personal_information_page",
})

PATIENT_HIDDEN_PAGE_STRINGS = frozenset({
    "datos fiscales",
    "fiscal data",
    "fiscal information",
})


def page_hidden_for_patients(name, string):
    """True si esa pestaña no se muestra en la ficha de un paciente."""
    technical = (name or "").strip()
    label = " ".join((string or "").split()).lower()
    if technical in PATIENT_HIDDEN_PAGE_NAMES:
        return True
    lowered = technical.lower()
    if "fiscal" in lowered and "personal" not in lowered:
        return True
    return label in PATIENT_HIDDEN_PAGE_STRINGS


# Marca de la fila DNI. El mixin de base pisa el string de todo vat con
# el rótulo del país (CUIT en Argentina) después del XML.
PATIENT_DNI_MARKER = "o_emr_patient_dni"


def is_patient_dni_node(invisible, class_attr):
    """La fila de documento del paciente, no el vat de los demás contactos."""
    if PATIENT_DNI_MARKER in (class_attr or "").split():
        return True
    return (invisible or "").strip() == "not is_patient"


def merge_invisible(current, extra="is_patient"):
    """Suma `extra` a un invisible que ya tenía la vista."""
    current = (current or "").strip()
    if not current:
        return extra
    if current == extra:
        return current
    return "(%s) or %s" % (current, extra)
