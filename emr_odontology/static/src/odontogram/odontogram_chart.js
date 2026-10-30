/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Mapa FDI. La notación es la de PERMANENT_QUADRANTS y DECIDUOUS_QUADRANTS
 * en emr_odontogram.py: derecha del paciente a la izquierda de la pantalla.
 *
 * El clic recorre un atajo (caries, obturación, ausente, sano, sin marca).
 * Corona, implante y el resto se cargan en la lista. Cada clic deja el
 * formulario modificado: se escribe al guardar, que es cuando la visita
 * actualiza el odontograma.
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

    get jaws() {
        const arches = this.arches;
        return [
            {
                key: "upper",
                lower: false,
                right: arches.upperRight,
                left: arches.upperLeft,
            },
            {
                key: "lower",
                lower: true,
                right: arches.lowerRight,
                left: arches.lowerLeft,
            },
        ];
    }

    get lines() {
        return this.props.record.data[this.props.name];
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

    conditionOf(fdi) {
        const rec = this.mark(fdi, this.state.surface);
        return (rec && rec.data.condition) || "";
    }

    hasOtherMark(fdi) {
        const list = this.lines;
        if (!list || !list.records) {
            return false;
        }
        return list.records.some(
            (rec) =>
                rec.data.fdi === fdi &&
                rec.data.surface &&
                rec.data.surface !== this.state.surface &&
                rec.data.condition
        );
    }

    toothClass(fdi, lower) {
        const classes = [
            "o_emr_odontogram_tooth",
            "o_emr_odontogram_cond_" + (this.conditionOf(fdi) || "empty"),
        ];
        if (lower) {
            classes.push("o_emr_odontogram_tooth_lower");
        }
        if (this.hasOtherMark(fdi)) {
            classes.push("o_emr_odontogram_tooth_more");
        }
        return classes.join(" ");
    }

    titleOf(fdi) {
        const rec = this.mark(fdi, this.state.surface);
        if (!rec || !rec.data.condition) {
            return fdi;
        }
        const cond = CONDITION_LABELS[rec.data.condition] || rec.data.condition;
        const status = STATUS_LABELS[rec.data.status] || rec.data.status || "";
        return status ? `${fdi}: ${cond} (${status})` : `${fdi}: ${cond}`;
    }

    setSurface(surface) {
        this.state.surface = surface;
    }

    toggleDeciduous() {
        this.state.deciduous = !this.state.deciduous;
    }

    async onTooth(fdi, ev) {
        if (ev) {
            ev.preventDefault();
            ev.stopPropagation();
        }
        if (this.props.readonly) {
            return;
        }
        const list = this.lines;
        if (!list) {
            return;
        }
        const surface = this.state.surface;
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
