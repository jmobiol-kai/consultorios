/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { EmrPatientHistory } from "@emr/patient_history/patient_history";

patch(EmrPatientHistory.prototype, {
    /**
     * Con mascota, la historia del costado es la del animal.
     * El partner de la atención es el dueño: sin este filtro se mezclan
     * todos sus animales.
     */
    async load(partnerId, encounterId) {
        const petId = this.many2oneId(this.props.record, "pet_id");
        if (!petId) {
            return super.load(partnerId, encounterId);
        }
        const orm = this.orm;
        this.orm = Object.assign(Object.create(orm), {
            call(model, method, args = [], kwargs = {}) {
                if (method === "get_patient_history") {
                    kwargs = {
                        ...kwargs,
                        context: { ...(kwargs.context || {}), emr_pet_id: petId },
                    };
                }
                return orm.call(model, method, args, kwargs);
            },
        });
        try {
            return await super.load(partnerId, encounterId);
        } finally {
            this.orm = orm;
        }
    },

    async printHistory() {
        const petId = this.many2oneId(this.props.record, "pet_id");
        if (!petId) {
            return super.printHistory(...arguments);
        }
        const action = await this.orm.call("emr.pet", "action_print_history", [[petId]]);
        if (action) {
            await this.action.doAction(action);
        }
    },
});
