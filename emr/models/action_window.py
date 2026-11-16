##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Acción de ventana que el cliente web de Odoo 19 puede abrir.

`doAction` hace `action.views.map(...)`. Sin `views`, el navegador tira
`Cannot read properties of undefined (reading 'map')`.
"""


def act_window_form(res_model, res_id, view_id=False, name=""):
    """Formulario de un registro, con la lista de vistas que pide el cliente."""
    return {
        "type": "ir.actions.act_window",
        "name": name or "",
        "res_model": res_model,
        "res_id": res_id,
        "view_mode": "form",
        "views": [[view_id or False, "form"]],
        "target": "current",
    }


def action_is_valid_for_do_action(action):
    """True si un act_window trae `views` como lista de pares [id, tipo]."""
    if not isinstance(action, dict):
        return False
    if action.get("type") != "ir.actions.act_window":
        return True
    views = action.get("views")
    if not isinstance(views, list) or not views:
        return False
    return all(
        isinstance(view, (list, tuple))
        and len(view) == 2
        and isinstance(view[1], str)
        and view[1]
        for view in views
    )
