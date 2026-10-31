/** @odoo-module **/

// Estado con el que nace cada condición al elegirla en la leyenda.
// Sano y ausente no se cobran. La obturación y el sellador quedan como
// hecho (es el acto). El resto entra "A tratar": es la práctica que la
// visita manda al presupuesto. En la lista de abajo se puede cambiar.
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
