/** @odoo-module **/

import { Component, markup, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * La historia del paciente, al costado de la atención que se está cargando.
 *
 * Ocupa el lugar del chatter y sigue sus mismas reglas de acomodo: al costado
 * cuando hay ancho, abajo cuando no.
 *
 * El resumen de cada atención lo dibuja el servidor con la plantilla del tipo
 * que corresponda; acá se agregan las acciones sobre cada una, que es la razón
 * de que sea un componente y no un campo html.
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
        this.state = useState({ entries: [], loaded: false, partnerId: false });

        onWillStart(() => this.load(this.props));
        onWillUpdateProps((next) => this.load(next));
    }

    async load(props) {
        const data = props.record.data;
        const partner = data.partner_id;
        const partnerId = Array.isArray(partner) ? partner[0] : partner && partner.id;
        this.state.partnerId = partnerId || false;
        if (!partnerId) {
            this.state.entries = [];
            this.state.loaded = true;
            return;
        }
        const encounter = data.encounter_id;
        const encounterId = Array.isArray(encounter)
            ? encounter[0]
            : encounter && encounter.id;

        const entries = await this.orm.call(
            "emr.encounter",
            "get_patient_history",
            [partnerId, encounterId || false]
        );
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

    async printEncounter(entry) {
        // El informe lo resuelve `emr.encounter.action_print`, que sabe cual es
        // el del tipo. Aca no se conoce el nombre del informe de cada tipo, ni
        // tiene que conocerse: los tipos los traen sus modulos.
        const action = await this.orm.call("emr.encounter", "action_print", [[entry.id]]);
        await this.action.doAction(action);
    }

    openEncounter(entry) {
        if (!entry.res_model || !entry.res_id) {
            return;
        }
        // En diálogo y no navegando: se está en el medio de cargar una
        // atención, y perderla de vista para mirar otra es peor que abrirla
        // al frente.
        //
        // Y en solo lectura: acá se viene a consultar qué le pasó antes al
        // paciente, no a corregirlo. Editar de paso una atención anterior,
        // desde el costado y sin haberla buscado, es la clase de cambio que
        // después nadie sabe explicar.
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: entry.res_model,
            res_id: entry.res_id,
            views: [[false, "form"]],
            target: "new",
            context: { form_view_initial_mode: "readonly" },
        });
    }
}
