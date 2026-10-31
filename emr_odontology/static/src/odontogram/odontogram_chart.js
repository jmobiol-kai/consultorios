/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import {
    clearTargets,
    conditionIsWholeTooth,
    cssColor,
    faceClickAction,
    legendPaintPlan,
    legendShowsActive,
    nextMark,
    paintCondition,
} from "./odontogram_chart_logic";

/**
 * Mapa FDI. Cada pieza es un círculo de cinco zonas: oclusal al centro y
 * las cuatro caras alrededor. Mesial mira a la línea media; vestibular
 * mira afuera de la arcada (arriba en el maxilar, abajo en la mandíbula).
 *
 * El primer clic en una cara la selecciona. Otro clic en la misma cara
 * borra la marca y la deja en blanco. No se recorren colores al hacer
 * clic. Con la cara seleccionada, el color se elige en la leyenda
 * (sano, caries, corona, …). Si el estado es de la pieza entera
 * (`whole_tooth` en el catálogo: corona, implante, prótesis, ausente,
 * sano, extracción indicada), se pinta el diente completo. El resto
 * pinta solo la cara elegida. La pieza entera también se elige con el
 * botón Pieza y el número; otro clic en el mismo número borra esa marca.
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

const NEED_SELECTION_HINT = "Primero hay que elegir una cara o la pieza en el mapa.";

// Círculo en viewBox 0 0 100 100. 0° es la derecha y crece en sentido
// horario, que es el sentido del arco SVG con y hacia abajo.
function polar(radius, deg) {
    const rad = (deg * Math.PI) / 180;
    return [50 + radius * Math.cos(rad), 50 + radius * Math.sin(rad)];
}

function slice(a0, a1) {
    const fmt = (n) => n.toFixed(2);
    const [x0, y0] = polar(46, a0);
    const [x1, y1] = polar(46, a1);
    const [xi1, yi1] = polar(20, a1);
    const [xi0, yi0] = polar(20, a0);
    return [
        `M ${fmt(x0)} ${fmt(y0)}`,
        `A 46 46 0 0 1 ${fmt(x1)} ${fmt(y1)}`,
        `L ${fmt(xi1)} ${fmt(yi1)}`,
        `A 20 20 0 0 0 ${fmt(xi0)} ${fmt(yi0)}`,
        "Z",
    ].join(" ");
}

const SLICES = {
    top: slice(225, 315),
    right: slice(315, 405),
    bottom: slice(45, 135),
    left: slice(135, 225),
};

export class OdontogramChartField extends Component {
    static template = "emr_odontology.OdontogramChart";
    static props = { ...standardFieldProps };

    setup() {
        this.surfaces = SURFACES;
        this.orm = useService("orm");
        this.state = useState({
            deciduous: false,
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

    regionStyle(fdi, surface) {
        const cond = paintCondition(
            surface,
            this.conditionOfSurface(fdi, surface),
            this.conditionOfSurface(fdi, "tooth")
        );
        const color = this.colorOf(cond);
        return color ? `fill:${color}` : "";
    }

    piezaStyle(fdi) {
        const color = this.colorOf(this.conditionOfSurface(fdi, "tooth") || "empty");
        return color ? `fill:${color};color:${color}` : "";
    }

    swatchStyle(code) {
        const color = this.colorOf(code);
        return color ? `background-color:${color}` : "";
    }

    get arches() {
        return this.state.deciduous ? DECIDUOUS : PERMANENT;
    }

    get quadrantLabels() {
        // Izquierda de la pantalla es la derecha del paciente.
        return this.state.deciduous
            ? { upperLeft: "5", upperRight: "6", lowerLeft: "8", lowerRight: "7" }
            : { upperLeft: "1", upperRight: "2", lowerLeft: "4", lowerRight: "3" };
    }

    get jaws() {
        const arches = this.arches;
        const labels = this.quadrantLabels;
        return [
            {
                key: "upper",
                lower: false,
                labelRight: labels.upperLeft,
                labelLeft: labels.upperRight,
                sides: [
                    { key: "right", teeth: arches.upperRight },
                    { key: "left", teeth: arches.upperLeft },
                ],
            },
            {
                key: "lower",
                lower: true,
                labelRight: labels.lowerLeft,
                labelLeft: labels.lowerRight,
                sides: [
                    { key: "right", teeth: arches.lowerRight },
                    { key: "left", teeth: arches.lowerLeft },
                ],
            },
        ];
    }

    get lines() {
        return this.props.record.data[this.props.name];
    }

    get selectionLabel() {
        const sel = this.state.selection;
        if (!sel) {
            return "";
        }
        const face = SURFACE_LABELS[sel.surface] || sel.surface;
        const own = this.conditionOfSurface(sel.fdi, sel.surface);
        const ownLabel = own ? this.conditionName(own) : "sin marca";
        const tooth = this.conditionOfSurface(sel.fdi, "tooth");
        const painted = paintCondition(sel.surface, own, tooth);
        let text = `Seleccionada: pieza ${sel.fdi} · ${face} (${ownLabel}).`;
        if (!own && painted !== "empty") {
            const paintedLabel = this.conditionName(painted);
            text += ` En el dibujo se ve ${paintedLabel} de la pieza.`;
        }
        text += " La condición se elige en la leyenda.";
        return text;
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
     * Mesial hacia la línea media. Vestibular hacia afuera de la boca:
     * arriba en el maxilar, abajo en la mandíbula.
     */
    facesFor(fdi, lower) {
        const mesialRight = ["1", "4", "5", "8"].includes(fdi[0]);
        return [
            { surface: lower ? "lingual" : "buccal", d: SLICES.top },
            { surface: mesialRight ? "mesial" : "distal", d: SLICES.right },
            { surface: lower ? "buccal" : "lingual", d: SLICES.bottom },
            { surface: mesialRight ? "distal" : "mesial", d: SLICES.left },
        ];
    }

    isSelected(fdi, surface) {
        const sel = this.state.selection;
        return Boolean(sel && sel.fdi === fdi && sel.surface === surface);
    }

    isToothSelected(fdi) {
        return Boolean(this.state.selection && this.state.selection.fdi === fdi);
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
        return `o_emr_odontogram_region o_emr_odontogram_cond_${cond}${active}`;
    }

    piezaClass(fdi) {
        const cond = this.conditionOfSurface(fdi, "tooth") || "empty";
        const active = this.isSelected(fdi, "tooth") ? " o_emr_odontogram_region_active" : "";
        return `o_emr_odontogram_pieza o_emr_odontogram_cond_${cond}${active}`;
    }

    fdiClass(fdi) {
        const missing = this.conditionOfSurface(fdi, "tooth") === "missing";
        const active = this.isToothSelected(fdi) ? " o_emr_odontogram_fdi_active" : "";
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
                return `${fdi} · ${face}. La pieza está en ${cond}.`;
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

    setSurface(surface) {
        this.state.surface = surface;
        if (this.state.selection) {
            this.state.selection = { fdi: this.state.selection.fdi, surface };
            this.state.hint = "";
        }
    }

    toggleDeciduous() {
        this.state.deciduous = !this.state.deciduous;
        this.state.selection = null;
        this.state.hint = "";
    }

    async onRegion(fdi, surface, ev) {
        if (ev) {
            ev.preventDefault();
            ev.stopPropagation();
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
        const surface = this.state.surface;
        if (faceClickAction(this.isSelected(fdi, surface)) === "clear") {
            await this.clearSelectionMark(fdi, surface);
            return;
        }
        this.select(fdi, surface);
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
    }

    async clearMark(fdi, surface) {
        if (this.props.readonly) {
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
        if (this.props.readonly) {
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
        if (this.props.readonly) {
            return;
        }
        const list = this.lines;
        if (!list) {
            return;
        }
        const existing = this.mark(fdi, surface);
        const next = nextMark(existing ? existing.data.condition : "", condition);
        // La leyenda pinta. No borra: eso es el segundo clic en la cara.
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
