##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Qué fichas recorre el paginador del odontograma, sin escribir nada.

No importa Odoo. La boca y cada consulta son filas de una vista SQL
(`emr.odontogram.page`). El id sale de la fila de origen, así que abrir
la pantalla no inserta, no renumera y no borra.

Odoo 19 no usa `res_ids` de la acción. En
`addons/web/static/src/webclient/actions/action_service.js`, `_getViewInfo`
copia `options.props` y solo lee `action.res_id`. En
`addons/web/static/src/views/form/form_controller.js`, `modelParams` arma
`resIds` con `this.props.resIds` o, si no viene, `[resId]`. El dominio
tampoco llena el paginador. Por eso Python devuelve una acción de cliente
y el JS abre el formulario con `doAction(acción, { props: { resIds } })`.
"""
from datetime import datetime


# La vista tiene que usar la misma cuenta. Par = odontograma, impar = consulta.
def chart_page_id(odontogram_id):
    return int(odontogram_id) * 2


def visit_page_id(odontology_id):
    return int(odontology_id) * 2 + 1


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


def procedure_summary(marks):
    """Texto corto de lo que se hizo: «Caries distal 14, Corona 36».

    `marks` es una lista de `(condición, cara, pieza)`. La cara «Pieza»
    es la pieza entera y no se repite. El orden de la lista se conserva.
    """
    parts = []
    for condition, surface, fdi in marks:
        bits = []
        label = " ".join(str(condition or "").split())
        face = " ".join(str(surface or "").split())
        tooth = " ".join(str(fdi or "").split())
        if label:
            bits.append(label)
        if face and face.lower() not in ("pieza", "tooth"):
            bits.append(face.lower())
        if tooth:
            bits.append(tooth)
        if bits:
            parts.append(" ".join(bits))
    return ", ".join(parts)


def pager_page_ids(odontogram_id, visit_ids):
    """Ids de la vista, en el orden de las flechas.

    El primero es el odontograma. Después van las consultas ya ordenadas.
    """
    return [chart_page_id(odontogram_id)] + [
        visit_page_id(visit_id) for visit_id in visit_ids
    ]


# Misma regla que is_empty_draft: state draft, sin pedido, sin texto,
# sin líneas y sin diagnósticos. btrim cubre el strip de espacios.
PAGE_VIEW_SQL = """
    SELECT
        o.id * 2 AS id,
        o.partner_id AS partner_id,
        'chart' AS kind,
        o.id AS odontogram_id,
        NULL::integer AS odontology_id,
        0 AS sequence
    FROM emr_odontogram o
    UNION ALL
    SELECT
        e.id * 2 + 1 AS id,
        enc.partner_id AS partner_id,
        'visit' AS kind,
        NULL::integer AS odontogram_id,
        e.id AS odontology_id,
        ROW_NUMBER() OVER (
            PARTITION BY enc.partner_id
            ORDER BY enc.date DESC NULLS LAST, e.id DESC
        )::integer AS sequence
    FROM emr_encounter_odontology e
    JOIN emr_encounter enc ON enc.id = e.encounter_id
    WHERE COALESCE(enc.active, TRUE)
      AND NOT (
            enc.state = 'draft'
            AND enc.order_id IS NULL
            AND btrim(COALESCE(e.reason, '')) = ''
            AND btrim(COALESCE(e.notes, '')) = ''
            AND NOT EXISTS (
                SELECT 1
                  FROM emr_encounter_odontology_line line
                 WHERE line.odontology_id = e.id
            )
            AND NOT EXISTS (
                SELECT 1
                  FROM emr_diagnosis_emr_encounter_rel rel
                 WHERE rel.emr_encounter_id = enc.id
            )
      )
"""


def odontogram_pager_client_action(view_id, page_ids, name, current_id=None):
    """Acción de cliente. El JS es quien pasa `resIds` en las props.

    `page_ids[0]` es el odontograma y ese orden no cambia. `current_id`,
    si está en la lista, es la ficha que se abre (una consulta desde la
    tabla). La acción de ventana que arma el JS lleva `views`, que Odoo 19
    exige, y no lleva `res_ids`: el cliente no lo leería.
    """
    ids = list(page_ids or [])
    if not ids:
        raise ValueError("el paginador necesita al menos el odontograma")
    current = current_id if current_id in ids else ids[0]
    return {
        "type": "ir.actions.client",
        "tag": "emr_odontogram_pager",
        "params": {
            "name": name or "",
            "res_model": "emr.odontogram.page",
            "res_id": current,
            "res_ids": ids,
            "views": [[view_id or False, "form"]],
            "context": {"create": False},
        },
    }


def window_action_from_pager_params(params):
    """La acción de ventana que el JS tiene que abrir, sin `res_ids`."""
    return {
        "type": "ir.actions.act_window",
        "name": params.get("name") or "",
        "res_model": params.get("res_model"),
        "res_id": params.get("res_id"),
        "view_mode": "form",
        "views": params.get("views"),
        "target": "current",
        "context": params.get("context") or {},
    }
