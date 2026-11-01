/** @odoo-module **/

import { Component, useEffect, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { encounterFormMustBeReadonly } from "./readonly_logic";

/**
 * Pasa el formulario a solo lectura cuando la visita ya no está en
 * elaboración, o cuando se abrió desde una tarjeta de la historia.
 *
 * En solo lectura no hay Guardar ni Descartar, y ningún campo acepta
 * cambios. Una atención en elaboración —Atender ahora— no entra acá.
 */
export class EmrEncounterReadonly extends Component {
    static props = standardWidgetProps;
    static template = xml`<t/>`;

    setup() {
        useEffect(
            () => {
                const record = this.props.record;
                const historyReadonly = Boolean(record.context?.emr_history_readonly);
                if (!encounterFormMustBeReadonly(record.data.state, historyReadonly)) {
                    return;
                }
                if (record.isInEdition) {
                    record.switchMode("readonly");
                }
            },
            () => {
                const record = this.props.record;
                return [
                    record.data.state,
                    Boolean(record.context?.emr_history_readonly),
                    record.isInEdition,
                ];
            }
        );
    }
}

registry.category("view_widgets").add("emr_encounter_readonly", {
    component: EmrEncounterReadonly,
    fieldDependencies: [{ name: "state", type: "selection" }],
});
