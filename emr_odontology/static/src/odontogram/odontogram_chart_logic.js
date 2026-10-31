/** @odoo-module **/

// Estado con el que nace cada condición al elegirla en la leyenda.
// Los valores son códigos (`pending`, `treated`), no el nombre que se
// edita en Configuración → Estados de la marca. Sano y ausente no se
// cobran. La obturación y el sellador quedan como hecho (es el acto).
// El resto entra "A tratar" (`pending`): es la práctica que la visita
// manda al presupuesto. En la lista de abajo se puede cambiar.
export const STATUS_FOR_CONDITION = {
    sound: "present",
    caries: "pending",
    restoration: "treated",
    crown: "pending",
    endodontics: "pending",
    implant: "pending",
    fracture: "pending",
    extraction: "pending",
    missing: "missing",
    prosthesis: "pending",
    sealant: "treated",
};

export function cssColor(value) {
    const color = String(value || "").trim().toLowerCase();
    return /^#[0-9a-f]{6}$/.test(color) ? color : "";
}

export function statusForCondition(condition) {
    return STATUS_FOR_CONDITION[condition] || "pending";
}

/**
 * Qué guarda un clic en la leyenda. Siempre aplica esa condición:
 * borrar es el segundo clic en la cara, no otro clic en la leyenda.
 *
 * @param {string} existingCondition condición actual, o ""
 * @param {string} condition condición elegida
 * @returns {{condition: string, status: string}}
 */
export function nextMark(existingCondition, condition) {
    return {
        condition,
        status: statusForCondition(condition),
        same: existingCondition === condition,
    };
}

/**
 * El clic en una cara no recorre colores.
 * La primera vez la selecciona; si ya era la selección, borra la marca.
 *
 * @param {boolean} alreadySelected
 * @returns {"select" | "clear"}
 */
export function faceClickAction(alreadySelected) {
    return alreadySelected ? "clear" : "select";
}

// Caras anatómicas. "tooth" es la pieza entera, no una cara.
export const FACE_SURFACES = ["mesial", "distal", "occlusal", "buccal", "lingual"];

// Códigos de fábrica. El mapa usa el campo `whole_tooth` del catálogo.
// Esta lista solo entra si esa fila no cargó.
export const WHOLE_TOOTH_CODES = new Set([
    "sound",
    "crown",
    "implant",
    "extraction",
    "missing",
    "prosthesis",
]);

/**
 * Si este estado pinta la pieza entera.
 *
 * Manda `row.whole_tooth` (Configuración → Estados de la pieza). El nombre no se
 * mira. Sin fila, o sin el campo, se usan los códigos de fábrica.
 *
 * @param {{ whole_tooth?: boolean | number } | null | undefined} row
 * @param {string} code
 * @returns {boolean}
 */
export function conditionIsWholeTooth(row, code) {
    if (row && row.whole_tooth !== undefined && row.whole_tooth !== null) {
        return row.whole_tooth === true || row.whole_tooth === 1;
    }
    return WHOLE_TOOTH_CODES.has(code);
}

/**
 * Dónde escribe un clic de la leyenda.
 *
 * Pieza entera: una sola marca en la pieza. Las caras sin marca propia
 * heredan ese color, así que hay que borrar las que ya tenían otra.
 * El resto pinta solo la cara seleccionada.
 *
 * @param {string} selectedSurface
 * @param {boolean} wholeTooth
 * @returns {{ write: string[], clear: string[] }}
 */
export function legendPaintPlan(selectedSurface, wholeTooth) {
    if (!wholeTooth) {
        return { write: [selectedSurface], clear: [] };
    }
    return { write: ["tooth"], clear: FACE_SURFACES.slice() };
}

/**
 * El botón de la leyenda queda activo si esa zona tiene el estado,
 * o si la cara está vacía y la pieza entera lo tiene.
 *
 * @param {string} own condición de la zona seleccionada, o ""
 * @param {string} tooth condición de la pieza, o ""
 * @param {string} condition estado del botón
 * @param {boolean} wholeTooth
 * @returns {boolean}
 */
export function legendShowsActive(own, tooth, condition, wholeTooth) {
    if (own === condition) {
        return true;
    }
    return Boolean(wholeTooth && !own && tooth === condition);
}

/**
 * Qué borra el segundo clic.
 *
 * Si la zona tiene marca, solo esa. Si la cara está vacía y el color
 * que se ve es el de la pieza entera, se borra la pieza: el color no
 * está en la cara, y si no se toca la pieza el diente no queda en blanco.
 *
 * @param {string} surface
 * @param {string} own
 * @param {string} tooth
 * @param {boolean} toothIsWhole
 * @returns {string[]}
 */
export function clearTargets(surface, own, tooth, toothIsWhole) {
    if (own) {
        return [surface];
    }
    if (surface !== "tooth" && tooth && toothIsWhole) {
        return ["tooth"];
    }
    return [];
}

/**
 * Color que se dibuja en una zona.
 *
 * La marca de la cara gana. Si la cara no tiene marca, se hereda la de
 * la pieza entera: el anillo de la pieza queda detrás de las caras y del
 * oclusal, así que sin esta herencia una corona (o cualquier otra
 * condición de la pieza) no se ve.
 *
 * @param {string} surface cara, o "tooth" para la pieza entera
 * @param {string} own condición de esa zona, o ""
 * @param {string} tooth condición de la pieza entera, o ""
 * @returns {string} clave de condición, o "empty"
 */
export function paintCondition(surface, own, tooth) {
    if (own) {
        return own;
    }
    if (surface !== "tooth" && tooth) {
        return tooth;
    }
    return "empty";
}
