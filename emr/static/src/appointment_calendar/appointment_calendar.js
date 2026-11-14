/** @odoo-module **/

import { calendarView } from "@web/views/calendar/calendar_view";
import { registry } from "@web/core/registry";

function toOdooDatetime(value) {
    if (!value || !value.toUTC) {
        return false;
    }
    return value.toUTC().toFormat("yyyy-MM-dd HH:mm:ss");
}

export class EmrAppointmentCalendarController extends calendarView.Controller {
    openWindowAction(xmlId) {
        this.action.doAction(xmlId);
    }

    /**
     * Un clic en una hora vacía abre el asistente del turno, con esa hora.
     * No crea una orden de venta a medias.
     */
    createRecord(record) {
        if (!this.model.canCreate) {
            return;
        }
        const start = toOdooDatetime(record && record.start);
        this.action.doAction("emr.emr_appointment_book_from_calendar_action", {
            additionalContext: {
                default_appointment_mode: "scheduled",
                default_start: start || false,
            },
        });
    }
}

registry.category("views").add("emr_appointment_calendar", {
    ...calendarView,
    Controller: EmrAppointmentCalendarController,
    buttonTemplate: "emr.AppointmentCalendarButtons",
});
