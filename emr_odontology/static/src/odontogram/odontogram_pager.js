/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Odoo 19 no lee action.res_ids.
 * action_service.js _getViewInfo solo copia options.props y action.res_id.
 * form_controller.js usa props.resIds, o [resId] si no vienen.
 * doAction(acción, { props: { resIds } }) es lo que llena las flechas.
 */
registry.category("actions").add("emr_odontogram_pager", async (env, action) => {
    const params = action.params || {};
    const resIds = params.res_ids || [];
    const resId = params.res_id || resIds[0];
    await env.services.action.doAction(
        {
            type: "ir.actions.act_window",
            name: params.name || "Odontograma",
            res_model: params.res_model,
            res_id: resId,
            views: params.views || [[false, "form"]],
            view_mode: "form",
            target: "current",
            context: params.context || {},
        },
        {
            props: {
                resId,
                resIds,
            },
        }
    );
});
