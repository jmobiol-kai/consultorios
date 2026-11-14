/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import {
    alignPrimarySlots,
    chartEditsAllowed,
    clearTargets,
    conditionIsWholeTooth,
    cssColor,
    faceClickAction,
    faceLayout,
    legendPaintPlan,
    legendShowsActive,
    nextMark,
    paintCondition,
    pendingOutline,
} from "./odontogram_chart_logic";

/**
 * Mapa FDI. Permanentes afuera y temporarias adentro, en la misma vista.
 * Cada pieza es un círculo de cinco zonas: oclusal al centro y las cuatro
 * caras alrededor. Mesial mira a la línea media; vestibular mira afuera
 * de la arcada (arriba en el maxilar, abajo en la mandíbula).
 *
 * El clic en una cara selecciona esa cara. El clic en el número selecciona
 * la pieza entera. Otro clic en la misma zona borra la marca. El color no
 * se recorre al hacer clic: se elige en la leyenda y es el de la condición.
 * A tratar lleva un borde rojo grueso; tratado y presente quedan con el
 * relleno solo. Otro clic en la misma condición pasa de a tratar a tratado.
 * La nota y el estado también están en el panel de la selección.
 * Se escribe al guardar, que es cuando la visita actualiza el odontograma.
 */

const PERMANENT = {
    upperRight: ["18", "17", "16", "15", "14", "13", "12", "11"],
    upperLeft: ["21", "22", "23", "24", "25", "26", "27", "28"],
    lowerRight: ["48", "47", "46", "45", "44", "43", "42", "41"],
    lowerLeft: ["31", "32", "33", "34", "35", "36", "37", "38"],
};

const DECIDUOUS = {
    upperRight: ["55", "54", "53", "52", "51"],
    upperLeft: ["61", "62", "63", "64", "65"],
    lowerRight: ["85", "84", "83", "82", "81"],
    lowerLeft: ["71", "72", "73", "74", "75"],
};

const SURFACES = [
    ["tooth", "Pieza"],
    ["mesial", "Mesial"],
    ["distal", "Distal"],
    ["occlusal", "Oclusal"],
    ["buccal", "Vestibular"],
    ["lingual", "Palatino"],
];

const SURFACE_LABELS = Object.fromEntries(SURFACES);

const CONDITION_LABELS = {
    sound: "Sano",
    caries: "Caries",
    restoration: "Obturación",
    crown: "Corona",
    endodontics: "Endodoncia",
    implant: "Implante",
    fracture: "Fractura",
    extraction: "Extracción indicada",
    missing: "Ausente",
    prosthesis: "Prótesis",
    sealant: "Sellador",
};

const STATUS_LABELS = {
    present: "Presente",
    pending: "A tratar",
    treated: "Tratado",
    missing: "Ausente",
    unerupted: "No erupcionado",
};

const LEGEND = Object.keys(CONDITION_LABELS).map((condition) => ({
    condition,
    label: CONDITION_LABELS[condition],
}));

const NEED_SELECTION_HINT = "Primero hay que elegir una cara o el número de la pieza.";
const NEED_CONDITION_HINT = "Elegí la condición en la leyenda.";

function dentitionRow(key, dentition, lower, labelRight, labelLeft, rightTeeth, leftTeeth) {
    const primary = dentition === "primary";
    return {
        key,
        dentition,
        lower,
        labelRight,
        labelLeft,
        sides: [
            {
                key: "right",
                slots: primary ? alignPrimarySlots(rightTeeth, true) : rightTeeth,
            },
            {
                key: "left",
                slots: primary ? alignPrimarySlots(leftTeeth, false) : leftTeeth,
            },
        ],
    };
}

export class OdontogramChartField extends Component {
    static template = "emr_odontology.OdontogramChart";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            surface: "tooth",
            selection: null,
            hint: "",
            conditions: [],
            statuses: [],
        });
        onWillStart(async () => {
            const load = async (model, fields) => {
                try {
                    return (
                        (await this.orm.searchRead(model, [], fields, {
                            context: { active_test: false },
                        })) || []
                    );
                } catch {
                    return [];
                }
            };
            const [conditions, statuses] = await Promise.all([
                load("emr.odontogram.condition", [
                    "code",
                    "name",
                    "color",
                    "sequence",
                    "active",
                    "whole_tooth",
                ]),
                load("emr.odontogram.status", ["code", "name", "sequence", "active"]),
            ]);
            this.state.conditions = conditions;
            this.state.statuses = statuses;
        });
    }

    get legend() {
        const rows = (this.state.conditions || [])
            .filter((row) => row.active !== false && row.code && row.name)
            .slice()
            .sort(
                (a, b) =>
                    (a.sequence || 0) - (b.sequence || 0) || (a.id || 0) - (b.id || 0)
            );
        if (!this.state.conditions.length) {
            return LEGEND;
        }
        return rows.map((row) => ({ condition: row.code, label: row.name }));
    }

    conditionName(code) {
        const row = (this.state.conditions || []).find((item) => item.code === code);
        if (row && row.name) {
            return row.name;
        }
        return CONDITION_LABELS[code] || code;
    }

    statusName(code) {
        const row = (this.state.statuses || []).find((item) => item.code === code);
        if (row && row.name) {
            return row.name;
        }
        return STATUS_LABELS[code] || code || "";
    }

    colorOf(code) {
        if (!code || code === "empty") {
            return "";
        }
        const row = (this.state.conditions || []).find((item) => item.code === code);
        return row ? cssColor(row.color) : "";
    }

    swatchStyle(code) {
        const color = this.colorOf(code);
        return color ? `background-color:${color}` : "";
    }

    get helpLine() {
        if (this.props.readonly) {
            // En la ficha el mapa es el estado actual, no una consulta cerrada.
            if (this.props.record.resModel === "res.partner") {
                return "Estado actual de la boca.";
            }
            return "Consulta registrada. El mapa no se modifica.";
        }
        const pending = this.statusName("pending");
        let text =
            `Clic en la cara, o en el número para la pieza entera. ` +
            `El borde rojo es ${pending.toLowerCase()}.`;
        if (this.props.record.resModel === "emr.odontogram") {
            text += " Corregir acá no se cobra.";
        }
        return text;
    }

    get jaws() {
        return [
            {
                key: "upper",
                rows: [
                    dentitionRow(
                        "upper-permanent",
                        "permanent",
                        false,
                        "1",
                        "2",
                        PERMANENT.upperRight,
                        PERMANENT.upperLeft
                    ),
                    dentitionRow(
                        "upper-primary",
                        "primary",
                        false,
                        "5",
                        "6",
                        DECIDUOUS.upperRight,
                        DECIDUOUS.upperLeft
                    ),
                ],
            },
            {
                key: "lower",
                rows: [
                    dentitionRow(
                        "lower-primary",
                        "primary",
                        true,
                        "8",
                        "7",
                        DECIDUOUS.lowerRight,
                        DECIDUOUS.lowerLeft
                    ),
                    dentitionRow(
                        "lower-permanent",
                        "permanent",
                        true,
                        "4",
                        "3",
                        PERMANENT.lowerRight,
                        PERMANENT.lowerLeft
                    ),
                ],
            },
        ];
    }

    get lines() {
        return this.props.record.data[this.props.name];
    }

    get panelTitle() {
        const sel = this.state.selection;
        if (!sel) {
            return "";
        }
        const face = SURFACE_LABELS[sel.surface] || sel.surface;
        const painted = this.selectedPaintedMark();
        if (!painted) {
            return `Pieza ${sel.fdi} · ${face}. ${NEED_CONDITION_HINT}`;
        }
        const cond = this.conditionName(painted.data.condition);
        const status = this.statusName(painted.data.status);
        return status
            ? `Pieza ${sel.fdi} · ${face} · ${cond} (${status})`
            : `Pieza ${sel.fdi} · ${face} · ${cond}`;
    }

    get selectedStatus() {
        const painted = this.selectedPaintedMark();
        return (painted && painted.data.status) || "";
    }

    get selectedNotes() {
        const painted = this.selectedPaintedMark();
        return (painted && painted.data.notes) || "";
    }

    get showStateButtons() {
        const painted = this.selectedPaintedMark();
        if (!painted) {
            return false;
        }
        const cond = painted.data.condition;
        return Boolean(cond && cond !== "sound" && cond !== "missing");
    }

    positionOf(fdi) {
        return fdi.slice(1);
    }

    mark(fdi, surface) {
        const list = this.lines;
        if (!list || !list.records) {
            return null;
        }
        return (
            list.records.find((rec) => rec.data.fdi === fdi && rec.data.surface === surface) ||
            null
        );
    }

    conditionOfSurface(fdi, surface) {
        const rec = this.mark(fdi, surface);
        return (rec && rec.data.condition) || "";
    }

    /**
     * La marca que se ve en la zona elegida. La de la cara gana; si no hay,
     * la de la pieza entera.
     */
    selectedPaintedMark() {
        const sel = this.state.selection;
        if (!sel) {
            return null;
        }
        const own = this.mark(sel.fdi, sel.surface);
        if (own && own.data.condition) {
            return own;
        }
        if (sel.surface !== "tooth") {
            const tooth = this.mark(sel.fdi, "tooth");
            if (tooth && tooth.data.condition) {
                return tooth;
            }
        }
        return null;
    }

    paintSource(fdi, surface) {
        const own = this.mark(fdi, surface);
        if (own && own.data.condition) {
            return own;
        }
        if (surface !== "tooth") {
            const tooth = this.mark(fdi, "tooth");
            if (tooth && tooth.data.condition) {
                return tooth;
            }
        }
        return null;
    }

    facesFor(fdi, lower) {
        return faceLayout(fdi, lower);
    }

    isSelected(fdi, surface) {
        const sel = this.state.selection;
        return Boolean(sel && sel.fdi === fdi && sel.surface === surface);
    }

    pendingClass(fdi, surface) {
        const src = this.paintSource(fdi, surface);
        return src && pendingOutline(src.data.status) ? " o_emr_odontogram_pending" : "";
    }

    regionClass(fdi, surface) {
        const cond = paintCondition(
            surface,
            this.conditionOfSurface(fdi, surface),
            this.conditionOfSurface(fdi, "tooth")
        );
        const active =
            this.isSelected(fdi, surface) || this.isSelected(fdi, "tooth")
                ? " o_emr_odontogram_region_active"
                : "";
        return `o_emr_odontogram_region o_emr_odontogram_cond_${cond}${this.pendingClass(fdi, surface)}${active}`;
    }

    regionStyle(fdi, surface) {
        const cond = paintCondition(
            surface,
            this.conditionOfSurface(fdi, surface),
            this.conditionOfSurface(fdi, "tooth")
        );
        const color = this.colorOf(cond);
        return color ? `fill:${color}` : "";
    }

    piezaClass(fdi) {
        const cond = this.conditionOfSurface(fdi, "tooth") || "empty";
        const active = this.isSelected(fdi, "tooth") ? " o_emr_odontogram_region_active" : "";
        return `o_emr_odontogram_pieza o_emr_odontogram_cond_${cond}${this.pendingClass(fdi, "tooth")}${active}`;
    }

    piezaStyle(fdi) {
        const color = this.colorOf(this.conditionOfSurface(fdi, "tooth") || "empty");
        return color ? `fill:${color};color:${color}` : "";
    }

    fdiClass(fdi) {
        const missing = this.conditionOfSurface(fdi, "tooth") === "missing";
        const active = this.isSelected(fdi, "tooth") ? " o_emr_odontogram_fdi_active" : "";
        const gone = missing ? " o_emr_odontogram_fdi_missing" : "";
        return `o_emr_odontogram_fdi${active}${gone}`;
    }

    regionTitle(fdi, surface) {
        const face = SURFACE_LABELS[surface] || surface;
        const rec = this.mark(fdi, surface);
        if (rec && rec.data.condition) {
            const cond = this.conditionName(rec.data.condition);
            const status = this.statusName(rec.data.status);
            return status ? `${fdi} · ${face}: ${cond} (${status})` : `${fdi} · ${face}: ${cond}`;
        }
        if (surface !== "tooth") {
            const tooth = this.mark(fdi, "tooth");
            if (tooth && tooth.data.condition) {
                const cond = this.conditionName(tooth.data.condition);
                const status = this.statusName(tooth.data.status);
                const extra = status ? ` (${status})` : "";
                return `${fdi} · ${face}. La pieza está en ${cond}${extra}.`;
            }
        }
        return `${fdi} · ${face}`;
    }

    isWholeTooth(condition) {
        const row = (this.state.conditions || []).find((item) => item.code === condition);
        return conditionIsWholeTooth(row, condition);
    }

    isLegendActive(condition) {
        const sel = this.state.selection;
        if (!sel) {
            return false;
        }
        return legendShowsActive(
            this.conditionOfSurface(sel.fdi, sel.surface),
            this.conditionOfSurface(sel.fdi, "tooth"),
            condition,
            this.isWholeTooth(condition)
        );
    }

    legendClass(condition) {
        const active = this.isLegendActive(condition) ? " o_emr_odontogram_legend_item_active" : "";
        return `o_emr_odontogram_legend_item${active}`;
    }

    legendTitle(condition) {
        const label = this.conditionName(condition);
        const sel = this.state.selection;
        if (!sel) {
            return `${label}. ${NEED_SELECTION_HINT}`;
        }
        const painted = this.selectedPaintedMark();
        if (
            painted &&
            painted.data.condition === condition &&
            (painted.data.status === "pending" || painted.data.status === "treated")
        ) {
            const next = painted.data.status === "pending" ? "treated" : "pending";
            return `${label}: pasar a ${this.statusName(next)}`;
        }
        if (this.isWholeTooth(condition)) {
            return `Marcar ${label} en toda la pieza ${sel.fdi}`;
        }
        const face = SURFACE_LABELS[sel.surface] || sel.surface;
        return `Marcar ${label} en la pieza ${sel.fdi} · ${face}`;
    }

    select(fdi, surface) {
        this.state.surface = surface;
        this.state.selection = { fdi, surface };
        this.state.hint = "";
    }

    async onRegion(fdi, surface, ev) {
        if (ev) {
            ev.preventDefault();
            ev.stopPropagation();
        }
        if (!chartEditsAllowed(this.props.readonly)) {
            return;
        }
        if (faceClickAction(this.isSelected(fdi, surface)) === "clear") {
            await this.clearSelectionMark(fdi, surface);
            return;
        }
        this.select(fdi, surface);
    }

    async onTooth(fdi, ev) {
        if (ev) {
            ev.preventDefault();
            ev.stopPropagation();
        }
        if (!chartEditsAllowed(this.props.readonly)) {
            return;
        }
        // El número es la pieza entera. La cara se elige en el dibujo.
        if (faceClickAction(this.isSelected(fdi, "tooth")) === "clear") {
            await this.clearSelectionMark(fdi, "tooth");
            return;
        }
        this.select(fdi, "tooth");
    }

    async clearSelectionMark(fdi, surface) {
        const own = this.conditionOfSurface(fdi, surface);
        const tooth = surface === "tooth" ? own : this.conditionOfSurface(fdi, "tooth");
        const targets = clearTargets(
            surface,
            own,
            tooth,
            Boolean(tooth) && this.isWholeTooth(tooth)
        );
        for (const target of targets) {
            await this.clearMark(fdi, target);
        }
        this.state.selection = null;
    }

    async clearMark(fdi, surface) {
        if (!chartEditsAllowed(this.props.readonly)) {
            return;
        }
        const list = this.lines;
        if (!list) {
            return;
        }
        const existing = this.mark(fdi, surface);
        if (existing) {
            await list.delete(existing);
        }
    }

    async onLegend(condition) {
        if (!chartEditsAllowed(this.props.readonly)) {
            return;
        }
        const sel = this.state.selection;
        if (!sel) {
            this.state.hint = NEED_SELECTION_HINT;
            return;
        }
        this.state.hint = "";
        const plan = legendPaintPlan(sel.surface, this.isWholeTooth(condition));
        for (const surface of plan.clear) {
            await this.clearMark(sel.fdi, surface);
        }
        for (const surface of plan.write) {
            await this.applyCondition(sel.fdi, surface, condition);
        }
    }

    async applyCondition(fdi, surface, condition) {
        if (!chartEditsAllowed(this.props.readonly)) {
            return;
        }
        const list = this.lines;
        if (!list) {
            return;
        }
        const existing = this.mark(fdi, surface);
        const next = nextMark(
            existing ? existing.data.condition : "",
            condition,
            existing ? existing.data.status : ""
        );
        // La misma condición en a tratar o tratado cambia el estado.
        // Borrar es el segundo clic en la cara.
        if (next.same) {
            return;
        }
        if (existing) {
            await existing.update({
                condition: next.condition,
                status: next.status,
            });
            return;
        }
        const created = await list.addNewRecord({
            position: "bottom",
            mode: "readonly",
            context: {
                default_fdi: fdi,
                default_surface: surface,
                default_condition: next.condition,
                default_status: next.status,
            },
        });
        if (
            created &&
            (created.data.fdi !== fdi ||
                created.data.surface !== surface ||
                created.data.condition !== next.condition ||
                created.data.status !== next.status)
        ) {
            await created.update({
                fdi,
                surface,
                condition: next.condition,
                status: next.status,
            });
        }
    }

    async setSelectedStatus(status) {
        if (!chartEditsAllowed(this.props.readonly)) {
            return;
        }
        const painted = this.selectedPaintedMark();
        if (!painted) {
            this.state.hint = NEED_CONDITION_HINT;
            return;
        }
        this.state.hint = "";
        if (painted.data.status === status) {
            return;
        }
        await painted.update({ status });
    }

    async onSelectedNotes(ev) {
        if (!chartEditsAllowed(this.props.readonly)) {
            return;
        }
        const painted = this.selectedPaintedMark();
        if (!painted) {
            this.state.hint = NEED_CONDITION_HINT;
            return;
        }
        const notes = ev.target.value || "";
        if ((painted.data.notes || "") === notes) {
            return;
        }
        await painted.update({ notes });
    }
}

registry.category("fields").add("odontogram_chart", {
    component: OdontogramChartField,
    supportedTypes: ["one2many"],
    // La lista embebida en la vista es la que carga los campos. Sin esto, el
    // parser arma una vista "default" y se pierde el subárbol.
    useSubView: true,
    relatedFields: [
        { name: "fdi", type: "selection", readonly: false },
        { name: "surface", type: "selection", readonly: false },
        { name: "condition", type: "selection", readonly: false },
        { name: "status", type: "selection", readonly: false },
        { name: "notes", type: "text", readonly: false },
    ],
});
