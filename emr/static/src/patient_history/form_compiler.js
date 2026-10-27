/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { append, createElement, setAttributes } from "@web/core/utils/xml";
import { FormCompiler } from "@web/views/form/form_compiler";
import { FormRenderer } from "@web/views/form/form_renderer";
import { EmrPatientHistory } from "./patient_history";

FormRenderer.components = {
    ...FormRenderer.components,
    EmrPatientHistory,
};

/**
 * Compila la etiqueta <patient_history/> del formulario.
 *
 * Es el mismo mecanismo con el que mail registra su <chatter/>: el nodo se
 * saca del sheet y se cuelga al lado, así queda en la columna del chatter en
 * vez de adentro de la hoja.
 */
function compilePatientHistory(node, params) {
    const hook = createElement("div");
    hook.classList.add("o-emr-PatientHistoryContainer");
    const component = createElement("t");
    setAttributes(component, {
        "t-component": "__comp__.constructor.components.EmrPatientHistory",
        record: "__comp__.props.record",
    });
    append(hook, component);
    return hook;
}

registry.category("form_compilers").add("emr_patient_history_compiler", {
    selector: "patient_history",
    fn: compilePatientHistory,
});

patch(FormCompiler.prototype, {
    compile(node, params) {
        const res = super.compile(node, params);
        const hook = res.querySelector(".o-emr-PatientHistoryContainer");
        if (!hook) {
            return res;
        }
        const sheetBg = res.querySelector(".o_form_sheet_bg");
        const parent = sheetBg && sheetBg.parentNode;
        if (!parent) {
            return res;
        }
        // Al costado cuando hay ancho, abajo cuando no: las mismas reglas que
        // usa el chatter.
        setAttributes(hook, {
            "t-attf-class":
                "{{ __comp__.env.isSmall ? 'mt-4' : 'o-aside w-print-100' }}",
        });
        append(parent, hook);
        return res;
    },
});
