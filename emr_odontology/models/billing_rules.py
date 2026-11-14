##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Reglas puras del presupuesto de la consulta.

No importan Odoo: los tests las leen sin levantar el servidor. El modelo
decide cuándo crear el pedido y qué borrador vacío se puede tirar.
"""


def needs_quotation(has_order, marks, billable_statuses, product_conditions):
    """True si hay prácticas cobrables y la visita todavía no tiene pedido.

    `marks` es una lista de pares (estado, condición). Sin prácticas, cerrar
    no inventa un presupuesto vacío.
    """
    if has_order:
        return False
    billable = set(billable_statuses)
    products = set(product_conditions)
    return any(status in billable and condition in products for status, condition in marks)


def cleanup_partner_ids(partner_ids):
    """Pacientes cuyos borradores vacíos se pueden tirar.

    Solo el mismo paciente. Un borrador sin paciente —la otra pestaña de
    Atender ahora, todavía sin elegir— no entra: Atendido no lo borra.
    """
    seen = []
    for partner_id in partner_ids or []:
        if partner_id and partner_id not in seen:
            seen.append(partner_id)
    return seen


def is_empty_draft(state, has_order, line_count, reason, notes, diagnosis_count=0):
    """Borrador sin paciente trabajado: no hay pedido, marcas, motivo ni nota.

    Es el que deja «Atender ahora» si se abre y no se carga nada. No es una
    consulta cerrada ni una que ya tenga presupuesto.
    """
    return (
        state == "draft"
        and not has_order
        and not line_count
        and not diagnosis_count
        and not (reason or "").strip()
        and not (notes or "").strip()
    )
