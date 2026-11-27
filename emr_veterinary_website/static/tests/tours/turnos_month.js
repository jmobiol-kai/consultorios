import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("emr_veterinary_website_turnos_month", {
    url: "/turnos",
    steps: () => [
        {
            content: "La grilla del mes muestra de lunes a domingo",
            trigger: ".o_emr_calendar .o_emr_weekdays span:nth-child(7)",
        },
        {
            content: "Los días del mes de al lado no van atenuados",
            trigger: ".o_emr_calendar .o_emr_week .o_emr_day",
            run() {
                const faded = document.querySelector(".o_emr_calendar .o_emr_day.is-out");
                if (faded) {
                    throw new Error("Un día de otro mes sigue atenuado");
                }
            },
        },
        {
            content: "Hay días en la grilla",
            trigger: ".o_emr_calendar .o_emr_week .o_emr_day",
            run: "click",
        },
        {
            content: "El título del día capitaliza solo la primera letra",
            trigger: ".o_emr_turnos.o_emr_mode_day .o_emr_title",
            run() {
                const title = document.querySelector(".o_emr_turnos .o_emr_title");
                const text = title ? title.textContent.trim() : "";
                if (!/^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+ \d+ de [a-záéíóúñ]+$/.test(text)) {
                    throw new Error(`Título inesperado: ${text}`);
                }
            },
        },
    ],
});
