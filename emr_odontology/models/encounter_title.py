##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Título del panel de la consulta odontológica.

No importa Odoo: el modelo solo aplica el texto. Sin esto, el panel
muestra el id técnico del modelo (emr.encounter.odontology,…).
"""

# Consulta nueva, todavía sin paciente. No puede ser vacío: el cliente
# de Odoo reemplaza un display_name vacío por «Nuevo», el mismo rótulo
# que el botón de la cabecera.
FALLBACK_TITLE = "Nueva consulta"


def encounter_control_panel_title(patient_name, fallback=FALLBACK_TITLE):
    """Nombre visible en el panel.

    Con paciente, el nombre del paciente. Sin paciente, el texto de una
    consulta nueva. Nunca el nombre técnico del modelo.
    """
    patient = (patient_name or "").strip()
    return patient or fallback
