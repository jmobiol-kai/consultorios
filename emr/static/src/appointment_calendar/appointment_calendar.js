/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { calendarView } from "@web/views/calendar/calendar_view";
import { registry } from "@web/core/registry";

const CLOSED_APPOINTMENT_STATES = new Set([
    "done",
    "validated",
    "cancelled",
    "no_show",
    "void",
]);

function toOdooDatetime(value) {
    if (!value || !value.toUTC) {
        return false;
    }
    return value.toUTC().toFormat("yyyy-MM-dd HH:mm:ss");
}

export class EmrAppointmentPopover extends CalendarCommonPopover {
    static subTemplates = {
        ...CalendarCommonPopover.subTemplates,
        footer: "emr.AppointmentCalendarPopover.footer",
    };

    setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
    }

    get canAttendNow() {
        const state = this.props.record.rawRecord.appointment_state;
        return !CLOSED_APPOINTMENT_STATES.has(state);
    }

    async onAttendNow(ev) {
        if (ev) {
            ev.preventDefault();
            ev.stopPropagation();
        }
        const action = await this.orm.call(
            "sale.order",
            "action_attend_now",
            [[this.props.record.id]]
        );
        this.props.close();
        if (action) {
            await this.action.doAction(action);
        }
    }
}

class EmrAppointmentCommonRenderer extends CalendarCommonRenderer {
    static components = {
        ...CalendarCommonRenderer.components,
        Popover: EmrAppointmentPopover,
    };
    // Hora y paciente en la misma línea, para que un hueco de 15 minutos
    // no se quede solo con la hora. El tipo de visita va debajo.
    static eventTemplate = "emr.AppointmentCalendarEvent";
}

class EmrAppointmentCalendarRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        day: EmrAppointmentCommonRenderer,
        week: EmrAppointmentCommonRenderer,
        month: EmrAppointmentCommonRenderer,
    };
}

export class EmrAppointmentCalendarController extends calendarView.Controller {
    openWindowAction(xmlId) {
        this.action.doAction(xmlId);
    }

    /**
     * Editar abre el formulario del turno, con `views`, que es lo que
     * doAction recorre. El formulario común de ventas no se usa acá.
     */
    async editRecord(record, context = {}) {
        if (!record || !record.id) {
            return super.editRecord(record, context);
        }
        const action = await this.orm.call(
            "sale.order",
            "action_open_appointment_form",
            [[record.id]]
        );
        if (action) {
            await this.action.doAction(action);
        }
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
    Renderer: EmrAppointmentCalendarRenderer,
    buttonTemplate: "emr.AppointmentCalendarButtons",
});
