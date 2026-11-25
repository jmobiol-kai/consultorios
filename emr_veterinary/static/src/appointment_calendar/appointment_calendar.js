/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { EmrAppointmentCalendarController } from "@emr/appointment_calendar/appointment_calendar";

function toOdooDatetime(value) {
    if (!value || !value.toUTC) {
        return false;
    }
    return value.toUTC().toFormat("yyyy-MM-dd HH:mm:ss");
}

function isVeterinary(controller) {
    const bags = [
        controller.props && controller.props.context,
        controller.model && controller.model.meta && controller.model.meta.context,
    ];
    return bags.some((ctx) => ctx && ctx.emr_veterinary);
}

patch(EmrAppointmentCalendarController.prototype, {
    createRecord(record) {
        if (!isVeterinary(this)) {
            return super.createRecord(...arguments);
        }
        if (!this.model.canCreate) {
            return;
        }
        const start = toOdooDatetime(record && record.start);
        this.action.doAction("emr.emr_appointment_book_from_calendar_action", {
            additionalContext: {
                default_appointment_mode: "scheduled",
                default_start: start || false,
                emr_veterinary: true,
            },
        });
    },
});
