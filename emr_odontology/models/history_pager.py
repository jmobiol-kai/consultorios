##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Qué fichas recorre el paginador del odontograma.

No importa Odoo. El formulario de Odoo solo pagina registros de un mismo
modelo: la boca actual y cada consulta son fichas de `emr.odontogram.page`,
en este orden. La primera es el mapa. Después van las consultas, de la
más nueva a la más vieja.
"""
from datetime import datetime


def history_visit_ids(visits):
    """Ids de consulta que entran al paginador, de la más nueva a la más vieja.

    `visits` es una lista de `(id, fecha, vacía)`. La fecha es datetime o
    un valor vacío. Un borrador vacío no es una consulta: es Atender ahora
    abierto y sin cargar. El resto entra, también si sigue en elaboración.
    """
    kept = []
    for visit_id, when, empty in visits:
        if empty or not visit_id:
            continue
        kept.append((visit_id, when or None))
    kept.sort(
        key=lambda item: (item[1] is not None, item[1] or datetime.min, item[0]),
        reverse=True,
    )
    return [visit_id for visit_id, _when in kept]


def odontogram_pager_action(view_id, page_ids, name):
    """Acción de formulario cuyo paginador recorre `page_ids` en ese orden.

    `page_ids[0]` es el odontograma actual. `views` es la lista que Odoo 19
    necesita para abrir la acción sin romper el cliente.
    """
    ids = list(page_ids or [])
    if not ids:
        raise ValueError("el paginador necesita al menos el odontograma")
    return {
        "type": "ir.actions.act_window",
        "name": name or "",
        "res_model": "emr.odontogram.page",
        "res_id": ids[0],
        "res_ids": ids,
        "view_mode": "form",
        "views": [[view_id or False, "form"]],
        "target": "current",
        "context": {"create": False},
    }
