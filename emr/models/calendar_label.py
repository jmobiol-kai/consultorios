##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Texto del turno en el calendario.

No importa Odoo. La hora la pone la vista; acá van el paciente y,
si entra, el tipo de visita en una segunda línea.
"""


def appointment_calendar_lines(patient_name, procedure_name):
    """Nombre del paciente y, aparte, el tipo de visita.

    El tipo se omite si está vacío o si repite el nombre del paciente.
    """
    patient = " ".join((patient_name or "").split())
    procedure = " ".join((procedure_name or "").split())
    if not procedure or procedure == patient:
        procedure = ""
    return patient, procedure
