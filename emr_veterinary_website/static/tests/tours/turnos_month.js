import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("emr_veterinary_website_turnos_month", {
    url: "/turnos",
    steps: () => [
        {
            content: "La grilla del mes muestra de lunes a domingo",
            trigger: ".o_emr_calendar .o_emr_weekdays span:nth-child(7)",
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
