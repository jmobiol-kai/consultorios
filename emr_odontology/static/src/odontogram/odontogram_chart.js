/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Mapa FDI. Cada pieza es un círculo de cinco zonas: oclusal al centro y
 * las cuatro caras alrededor. Mesial mira a la línea media; vestibular
 * mira afuera de la arcada (arriba en el maxilar, abajo en la mandíbula).
 *
 * Un clic en una zona marca esa cara de esa pieza. Los botones siguen
 * eligiendo la cara —incluida la pieza entera, que no es una zona del
 * dibujo— y el número FDI de abajo la aplica.
 *
 * El clic recorre un atajo (caries, obturación, ausente, sano, sin marca).
 * Corona, implante y el resto se cargan en la lista. Se escribe al guardar,
 * que es cuando la visita actualiza el odontograma.
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

const CYCLE = [
    { condition: "caries", status: "pending" },
    { condition: "restoration", status: "treated" },
    { condition: "missing", status: "missing" },
    { condition: "sound", status: "present" },
];

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
        this.legend = LEGEND;
        this.state = useState({ deciduous: false, surface: "tooth" });
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

    regionClass(fdi, surface) {
        const cond = this.conditionOfSurface(fdi, surface) || "empty";
        const active = this.state.surface === surface ? " o_emr_odontogram_region_active" : "";
        return `o_emr_odontogram_region o_emr_odontogram_cond_${cond}${active}`;
    }

    piezaClass(fdi) {
        const cond = this.conditionOfSurface(fdi, "tooth") || "empty";
        const active = this.state.surface === "tooth" ? " o_emr_odontogram_region_active" : "";
        return `o_emr_odontogram_pieza o_emr_odontogram_cond_${cond}${active}`;
    }

    fdiClass(fdi) {
        const missing = this.conditionOfSurface(fdi, "tooth") === "missing";
        const active = this.state.surface === "tooth" ? " o_emr_odontogram_fdi_active" : "";
        const gone = missing ? " o_emr_odontogram_fdi_missing" : "";
        return `o_emr_odontogram_fdi${active}${gone}`;
    }

    regionTitle(fdi, surface) {
        const face = SURFACE_LABELS[surface] || surface;
        const rec = this.mark(fdi, surface);
        if (!rec || !rec.data.condition) {
            return `${fdi} · ${face}`;
        }
        const cond = CONDITION_LABELS[rec.data.condition] || rec.data.condition;
        const status = STATUS_LABELS[rec.data.status] || rec.data.status || "";
        return status ? `${fdi} · ${face}: ${cond} (${status})` : `${fdi} · ${face}: ${cond}`;
    }

    setSurface(surface) {
        this.state.surface = surface;
    }

    toggleDeciduous() {
        this.state.deciduous = !this.state.deciduous;
    }

    async onRegion(fdi, surface, ev) {
        if (ev) {
            ev.preventDefault();
            ev.stopPropagation();
        }
        this.state.surface = surface;
        await this.applyMark(fdi, surface);
    }

    async onTooth(fdi, ev) {
        if (ev) {
            ev.preventDefault();
            ev.stopPropagation();
        }
        await this.applyMark(fdi, this.state.surface);
    }

    async applyMark(fdi, surface) {
        if (this.props.readonly) {
            return;
        }
        const list = this.lines;
        if (!list) {
            return;
        }
        const existing = this.mark(fdi, surface);
        const index = existing
            ? CYCLE.findIndex((step) => step.condition === existing.data.condition)
            : -1;
        if (existing && index === CYCLE.length - 1) {
            await list.delete(existing);
            return;
        }
        const step = CYCLE[index + 1] || CYCLE[0];
        if (existing) {
            await existing.update({
                condition: step.condition,
                status: step.status,
            });
            return;
        }
        const created = await list.addNewRecord({
            position: "bottom",
            mode: "readonly",
            context: {
                default_fdi: fdi,
                default_surface: surface,
                default_condition: step.condition,
                default_status: step.status,
            },
        });
        if (
            created &&
            (created.data.fdi !== fdi ||
                created.data.surface !== surface ||
                created.data.condition !== step.condition ||
                created.data.status !== step.status)
        ) {
            await created.update({
                fdi,
                surface,
                condition: step.condition,
                status: step.status,
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
