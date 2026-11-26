import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

const WEEKDAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const MONTHS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

function iso(date) {
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${date.getFullYear()}-${month}-${day}`;
}

function parseDay(value) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day);
}

function capitalizeFirst(value) {
    if (!value) {
        return "";
    }
    return value.charAt(0).toLocaleUpperCase("es") + value.slice(1);
}

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) {
        node.className = className;
    }
    if (text !== undefined) {
        node.textContent = text;
    }
    return node;
}

export class TurnosCalendar extends Interaction {
    static selector = ".o_emr_turnos";

    setup() {
        const today = new Date();
        this.today = new Date(today.getFullYear(), today.getMonth(), today.getDate());
        this.view = new Date(this.today.getFullYear(), this.today.getMonth(), 1);
        this.mode = "month";
        this.selectedDay = null;
        this.selectedSlot = null;
        this.payload = { slots: [], practitioners: [], today: iso(this.today) };
        this.calendarEl = this.el.querySelector(".o_emr_calendar");
        this.miniEl = this.el.querySelector(".o_emr_mini");
        this.titleEl = this.el.querySelector(".o_emr_title");
        this.formEl = this.el.querySelector("#emr_booking");
        this.summaryEl = this.el.querySelector(".o_emr_summary");
        this.filterEl = this.el.querySelector(".o_emr_filter");
    }

    start() {
        this.addListener(this.el, "click", this.onClick);
        this.addListener(this.filterEl, "change", () => this.load());
        this.addListener(window, "resize", () => this.render());
        const species = this.el.querySelector("#emr_species");
        if (species) {
            this.addListener(species, "change", () => this.filterBreeds());
            this.filterBreeds();
        }
        this.load();
    }

    professionalId() {
        return this.filterEl.value || "";
    }

    async load() {
        const grid = this.monthDays(this.view);
        const flat = grid.flat();
        const start = iso(flat[0]);
        const end = iso(flat[flat.length - 1]);
        const query = new URLSearchParams({ start, end });
        if (this.professionalId()) {
            query.set("professional_id", this.professionalId());
        }
        const response = await this.waitFor(fetch(`/turnos/huecos?${query}`));
        this.payload = await this.waitFor(response.json());
        if (this.payload.today) {
            this.today = parseDay(this.payload.today);
        }
        this.render();
    }

    monthDays(monthDate) {
        const first = new Date(monthDate.getFullYear(), monthDate.getMonth(), 1);
        const offset = (first.getDay() + 6) % 7;
        const start = new Date(first);
        start.setDate(first.getDate() - offset);
        const weeks = [];
        for (let week = 0; week < 6; week++) {
            const days = [];
            for (let day = 0; day < 7; day++) {
                const date = new Date(start);
                date.setDate(start.getDate() + week * 7 + day);
                days.push(date);
            }
            weeks.push(days);
        }
        return weeks;
    }

    slotsOn(dayIso) {
        return (this.payload.slots || []).filter((slot) => slot.date === dayIso);
    }

    practitioner(id) {
        return (this.payload.practitioners || []).find((item) => item.id === id) || {
            id,
            name: "",
            color_hex: "#875A7B",
        };
    }

    render() {
        const label = this.mode === "day" && this.selectedDay
            ? this.dayLabel(this.selectedDay)
            : `${MONTHS[this.view.getMonth()]} ${this.view.getFullYear()}`;
        this.titleEl.textContent = capitalizeFirst(label);
        this.el.classList.toggle("o_emr_mode_day", this.mode === "day");
        this.el.querySelector(".o_emr_back").classList.toggle("d-none", this.mode !== "day");
        this.renderMini();
        this.calendarEl.replaceChildren();
        if (this.mode === "day" && this.selectedDay) {
            this.renderDay(this.selectedDay);
        } else {
            this.renderMonth();
        }
    }

    renderMini() {
        this.miniEl.replaceChildren();
        const head = el("div", "o_emr_weekdays");
        WEEKDAYS.forEach((name) => head.append(el("span", "", name[0])));
        this.miniEl.append(head);
        this.monthDays(this.view).forEach((week) => {
            const row = el("div", "o_emr_week");
            week.forEach((date) => row.append(this.dayButton(date, true)));
            this.miniEl.append(row);
        });
    }

    renderMonth() {
        const head = el("div", "o_emr_weekdays");
        WEEKDAYS.forEach((name) => head.append(el("span", "", name)));
        this.calendarEl.append(head);
        this.monthDays(this.view).forEach((week) => {
            const row = el("div", "o_emr_week");
            week.forEach((date) => row.append(this.dayButton(date, false)));
            this.calendarEl.append(row);
        });
    }

    dayButton(date, mini) {
        const dayIso = iso(date);
        const slots = this.slotsOn(dayIso);
        const past = date < this.today;
        const outside = date.getMonth() !== this.view.getMonth();
        const muted = past || !slots.length;
        const button = el("button", "o_emr_day");
        button.type = "button";
        button.dataset.day = dayIso;
        if (muted) {
            button.classList.add("is-muted");
        }
        if (outside) {
            button.classList.add("is-out");
        }
        if (dayIso === iso(this.today)) {
            button.classList.add("is-today");
        }
        button.append(el("span", "o_emr_num", String(date.getDate())));
        if (!mini && !muted) {
            const seen = new Set();
            slots.forEach((slot) => seen.add(slot.practitioner_id));
            seen.forEach((id) => {
                const vet = this.practitioner(id);
                const chip = el("span", "o_emr_chip", vet.name);
                chip.style.background = vet.color_hex;
                const dot = el("span", "o_emr_dot");
                dot.style.background = vet.color_hex;
                dot.title = vet.name;
                dot.setAttribute("aria-label", vet.name);
                button.append(chip, dot);
            });
        }
        return button;
    }

    renderDay(date) {
        const slots = this.slotsOn(iso(date));
        const narrow = window.matchMedia("(max-width: 767.98px)").matches;
        if (!slots.length) {
            this.calendarEl.append(el("p", "text-muted", "No hay horarios libres este día."));
            return;
        }
        if (narrow) {
            this.renderDayList(slots);
        } else {
            this.renderDayGrid(slots);
        }
    }

    renderDayList(slots) {
        const list = el("div", "o_emr_daylist");
        const ids = [...new Set(slots.map((slot) => slot.practitioner_id))];
        ids.forEach((id) => {
            const vet = this.practitioner(id);
            list.append(el("h3", "h6 mt-3", vet.name));
            slots.filter((slot) => slot.practitioner_id === id).forEach((slot) => {
                list.append(this.slotButton(slot, vet, false));
            });
        });
        this.calendarEl.append(list);
    }

    renderDayGrid(slots) {
        const ids = [...new Set(slots.map((slot) => slot.practitioner_id))];
        const minutes = slots.flatMap((slot) => [this.minutes(slot.start), this.minutes(slot.stop)]);
        const from = Math.floor(Math.min(...minutes) / 60) * 60;
        const to = Math.ceil(Math.max(...minutes) / 60) * 60;
        const grid = el("div", "o_emr_daygrid");
        grid.style.setProperty("--emr-cols", String(ids.length));
        grid.append(el("div", "o_emr_colhead", ""));
        ids.forEach((id) => grid.append(el("div", "o_emr_colhead", this.practitioner(id).name)));
        const height = ((to - from) / 30) * 28;
        grid.append(this.hourColumn(from, to));
        ids.forEach((id) => {
            const column = el("div", "o_emr_col");
            column.style.height = `${height}px`;
            slots.filter((slot) => slot.practitioner_id === id).forEach((slot) => {
                const vet = this.practitioner(id);
                const block = this.slotButton(slot, vet, true);
                const top = ((this.minutes(slot.start) - from) / 30) * 28;
                const span = Math.max(this.minutes(slot.stop) - this.minutes(slot.start), 30);
                block.style.top = `${top}px`;
                block.style.height = `${(span / 30) * 28 - 2}px`;
                column.append(block);
            });
            grid.append(column);
        });
        this.calendarEl.append(grid);
    }

    hourColumn(from, to) {
        const column = el("div", "o_emr_hours");
        for (let minute = from; minute < to; minute += 60) {
            const hour = String(Math.floor(minute / 60)).padStart(2, "0");
            const label = el("div", "o_emr_hour", `${hour}:00`);
            label.style.height = "56px";
            column.append(label);
        }
        return column;
    }

    slotButton(slot, vet, absolute) {
        const button = el("button", absolute ? "o_emr_block" : "o_emr_block", `${slot.start}–${slot.stop}`);
        button.type = "button";
        button.dataset.slot = String(slot.id);
        button.style.background = vet.color_hex;
        if (this.selectedSlot && this.selectedSlot.id === slot.id) {
            button.classList.add("is-selected");
        }
        return button;
    }

    minutes(value) {
        const [hour, minute] = value.split(":").map(Number);
        return hour * 60 + minute;
    }

    dayLabel(date) {
        const weekday = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"][date.getDay()];
        return `${weekday} ${date.getDate()} de ${MONTHS[date.getMonth()]}`;
    }

    onClick(event) {
        const nav = event.target.closest("[data-nav]");
        if (nav) {
            this.onNav(nav.dataset.nav);
            return;
        }
        const slotButton = event.target.closest("[data-slot]");
        if (slotButton) {
            const slot = (this.payload.slots || []).find((item) => String(item.id) === slotButton.dataset.slot);
            if (slot) {
                this.choose(slot);
            }
            return;
        }
        const dayButton = event.target.closest("[data-day]");
        if (dayButton) {
            this.openDay(parseDay(dayButton.dataset.day));
        }
    }

    onNav(action) {
        if (action === "today") {
            this.view = new Date(this.today.getFullYear(), this.today.getMonth(), 1);
            this.selectedDay = new Date(this.today);
            this.mode = "day";
            this.load();
            return;
        }
        if (action === "month") {
            this.mode = "month";
            this.render();
            return;
        }
        const step = action === "next" ? 1 : -1;
        if (this.mode === "day" && this.selectedDay) {
            const next = new Date(this.selectedDay);
            next.setDate(next.getDate() + step);
            this.openDay(next);
            return;
        }
        this.view = new Date(this.view.getFullYear(), this.view.getMonth() + step, 1);
        this.load();
    }

    openDay(date) {
        const monthChanged = date.getMonth() !== this.view.getMonth()
            || date.getFullYear() !== this.view.getFullYear();
        this.selectedDay = date;
        this.view = new Date(date.getFullYear(), date.getMonth(), 1);
        this.mode = "day";
        if (monthChanged) {
            this.load();
            return;
        }
        this.render();
    }

    choose(slot) {
        this.selectedSlot = slot;
        const vet = this.practitioner(slot.practitioner_id);
        this.formEl.classList.remove("d-none");
        this.formEl.querySelector("[name='slot_id']").value = slot.id;
        this.formEl.querySelector("[name='practitioner_id']").value = slot.practitioner_id;
        const day = parseDay(slot.date);
        this.summaryEl.textContent = `${this.dayLabel(day)} · ${slot.start} · ${vet.name}`;
        this.render();
        this.formEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    filterBreeds() {
        const species = this.el.querySelector("#emr_species");
        const breed = this.el.querySelector("#emr_breed");
        if (!species || !breed) {
            return;
        }
        [...breed.options].forEach((option) => {
            if (!option.value) {
                option.hidden = false;
                return;
            }
            option.hidden = Boolean(species.value) && option.dataset.species !== species.value;
        });
    }
}

registry.category("public.interactions").add("emr_veterinary_website.turnos", TurnosCalendar);
