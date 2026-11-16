/** @odoo-module **/

import { onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

/**
 * El paginador solo recuerda props.resIds. Una recarga, la miga de pan o
 * un botón que abre el formulario directo dejan una sola ficha. Acá se
 * piden los ids al servidor, que no escribe.
 */
export class EmrOdontogramPageFormController extends FormController {
    setup() {
        super.setup();
        onMounted(() => this.fillPagerIds());
    }

    async fillPagerIds() {
        const current = this.model.root?.resIds || [];
        if (current.length > 1) {
            return;
        }
        const resId = this.model.root?.resId;
        if (!resId) {
            return;
        }
        const ids = await this.orm.call("emr.odontogram.page", "pager_ids_for", [[resId]]);
        if (!Array.isArray(ids) || ids.length < 2 || !ids.includes(resId)) {
            return;
        }
        await this.model.load({ resId, resIds: ids });
    }
}

registry.category("views").add("emr_odontogram_page", {
    ...formView,
    Controller: EmrOdontogramPageFormController,
});
