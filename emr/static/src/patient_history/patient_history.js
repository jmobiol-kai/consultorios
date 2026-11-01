/** @odoo-module **/

import { Component, markup, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

/**
 * La historia del paciente, al costado de la atención que se está cargando.
 *
 * Ocupa el lugar del chatter y sigue sus mismas reglas de acomodo: al costado
 * cuando hay ancho, abajo cuando no.
 *
 * El resumen de cada atención lo dibuja el servidor con la plantilla del tipo
 * que corresponda. El renglón entero abre esa atención, en solo lectura; el
 * PDF de la historia completa queda en el encabezado del panel.
 *
 * El paciente se puede elegir en la misma pantalla, antes de que exista un
 * presupuesto. El panel se vuelve a armar cuando cambia ese campo: el
 * formulario no redibuja todo el costado por sí solo.
 */
export class EmrPatientHistory extends Component {
    static template = "emr.PatientHistory";
    static props = {
        record: { type: Object },
        isAside: { type: Boolean, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.state = useState({ entries: [], loaded: false, partnerId: false });
        this._loadSeq = 0;
        this._loadedKey = undefined;
        this._inflight = undefined;

        // Lee partner_id (y la visita, si está en el formulario) para
        // suscribirse: cuando la secretaria elige otro paciente, esto corre
        // de nuevo y el costado muestra esa historia.
        useRecordObserver((record) => {
            this.load(this.many2oneId(record, "partner_id"), this.many2oneId(record, "encounter_id"));
        });
    }

    many2oneId(record, name) {
        // La receta también usa este panel y no tiene encounter_id en la
        // vista. No se lee un campo que el formulario no cargó.
        try {
            const active = record.activeFields;
            if (active && !active[name]) {
                return false;
            }
            const value = record.data[name];
            if (!value) {
                return false;
            }
            if (Array.isArray(value)) {
                return value[0] || false;
            }
            return value.id || false;
        } catch {
            return false;
        }
    }

    async load(partnerId, encounterId) {
        const key = `${partnerId || 0}:${encounterId || 0}`;
        if (this._loadedKey === key && (this.state.loaded || this._inflight === key)) {
            return;
        }
        this._loadedKey = key;
        this._inflight = key;
        const seq = ++this._loadSeq;
        this.state.partnerId = partnerId || false;
        if (!partnerId) {
            this.state.entries = [];
            this.state.loaded = true;
            this._inflight = undefined;
            return;
        }
        // Mientras llega la historia nueva no se dejan las tarjetas del
        // paciente anterior.
        this.state.loaded = false;
        let entries;
        try {
            entries = await this.orm.call(
                "emr.encounter",
                "get_patient_history",
                [partnerId, encounterId || false]
            );
        } catch {
            if (seq !== this._loadSeq) {
                return;
            }
            // El servicio RPC ya mostró el error. Se suelta la carga para
            // que elegir de nuevo al paciente vuelva a pedir la historia.
            this._inflight = undefined;
            this._loadedKey = undefined;
            this.state.entries = [];
            this.state.loaded = true;
            return;
        }
        if (seq !== this._loadSeq) {
            return;
        }
        this._inflight = undefined;
        // El resumen viaja como texto por RPC y t-out escapa las cadenas. Se
        // marca como markup para que se dibuje: el html lo genera el servidor
        // con nuestras propias plantillas, que ya escapan los valores.
        this.state.entries = entries.map((entry) => ({
            ...entry,
            html: markup(entry.html),
        }));
        this.state.loaded = true;
    }

    async printHistory() {
        // La accion la arma el servidor: es el mismo boton que la ficha del
        // paciente, con su control de que sea un paciente y su informe.
        if (!this.state.partnerId) {
            return;
        }
        const action = await this.orm.call("res.partner", "action_print_history", [
            [this.state.partnerId],
        ]);
        await this.action.doAction(action);
    }

    onEntryKeydown(ev, entry) {
        // El renglón es un botón: Enter y Espacio hacen lo mismo que el clic.
        if (ev.key !== "Enter" && ev.key !== " ") {
            return;
        }
        ev.preventDefault();
        this.openEncounter(entry);
    }

    openEncounter(entry) {
        if (!entry.res_model || !entry.res_id) {
            return;
        }
        // En diálogo y no navegando: se está en el medio de cargar una
        // atención, y perderla de vista para mirar otra es peor que abrirla
        // al frente.
        //
        // Y en solo lectura de verdad. Odoo 19 ya no mira
        // form_view_initial_mode, y un act_window con target "new" abre el
        // formulario en edición: por eso se veían Guardar y Descartar y el
        // odontograma seguía seleccionando caras. Esta tarjeta es para
        // consultar qué le pasó antes al paciente, aunque la visita haya
        // quedado en elaboración. No se expande: expandir abriría el mismo
        // formulario en edición y se perdería la atención de abajo.
        this.dialog.add(FormViewDialog, {
            resModel: entry.res_model,
            resId: entry.res_id,
            title: "Consulta",
            readonly: true,
            preventCreate: true,
            preventEdit: true,
            canExpand: false,
            size: "xl",
            context: { emr_history_readonly: true },
        });
    }
}
