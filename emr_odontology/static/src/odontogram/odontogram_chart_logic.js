/** @odoo-module **/

// Estado con el que nace cada condición al elegirla en la leyenda.
// Los valores son códigos (`pending`, `treated`), no el nombre que se
// edita en Configuración → Estados del procedimiento. Sano y ausente no se
// cobran. La obturación y el sellador quedan como hecho (es el acto).
// El resto entra "A tratar" (`pending`): es la práctica que la visita
// manda al presupuesto. Otro clic en la misma condición pasa de
// `pending` a `treated` (y al revés). No hace falta la grilla.
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

// El relleno es el color de la condición (el de la leyenda). A tratar no
// cambia ese color: se marca con un borde rojo grueso. Tratado y presente
// quedan con el trazo fino de siempre.
export const PENDING_OUTLINE = "#c62828";

export function cssColor(value) {
    const color = String(value || "").trim().toLowerCase();
    return /^#[0-9a-f]{6}$/.test(color) ? color : "";
}

export function statusForCondition(condition) {
    return STATUS_FOR_CONDITION[condition] || "pending";
}

/**
 * A tratar lleva borde rojo. Tratado, presente y el resto no: el relleno
 * de la condición alcanza para leerlos.
 *
 * @param {string} status
 * @returns {boolean}
 */
export function pendingOutline(status) {
    return status === "pending";
}

/**
 * Qué guarda un clic en la leyenda.
 *
 * Otra condición: se aplica con el estado inicial de esa condición.
 * La misma condición, en "a tratar" o "tratado": cambia el estado.
 * Así una corona a tratar pasa a tratada sin la grilla. Borrar sigue
 * siendo el segundo clic en la cara, no la leyenda.
 *
 * @param {string} existingCondition condición actual, o ""
 * @param {string} condition condición elegida
 * @param {string} [existingStatus] estado actual, o ""
 * @returns {{condition: string, status: string, same: boolean}}
 */
export function nextMark(existingCondition, condition, existingStatus) {
    const status = statusForCondition(condition);
    if (existingCondition !== condition) {
        return { condition, status, same: false };
    }
    if (existingStatus === "pending") {
        return { condition, status: "treated", same: false };
    }
    if (existingStatus === "treated") {
        return { condition, status: "pending", same: false };
    }
    return {
        condition,
        status: existingStatus || status,
        same: true,
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
 * Una consulta cerrada, firmada o abierta desde la historia no selecciona
 * caras ni aplica la leyenda. `readonly` es el del campo (o del formulario).
 *
 * @param {boolean} readonly
 * @returns {boolean}
 */
export function chartEditsAllowed(readonly) {
    return !readonly;
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

/**
 * Las cinco temporarias de un cuadrante, en las ocho columnas de las
 * permanentes. Quedan del lado de la línea media: los molares
 * permanentes (18-16, 26-28, …) no tienen temporaria debajo.
 *
 * `distalOnLeft` es un cuadrante de la derecha del paciente (en pantalla,
 * la izquierda): el primer FDI de la lista es el más distal.
 *
 * @param {string[]} teeth cinco FDI en el orden en que se dibujan
 * @param {boolean} distalOnLeft
 * @returns {(string|null)[]}
 */
export function alignPrimarySlots(teeth, distalOnLeft) {
    const slots = [null, null, null, null, null, null, null, null];
    const list = (teeth || []).slice(0, 5);
    if (distalOnLeft) {
        list.forEach((fdi, i) => {
            slots[3 + i] = fdi;
        });
    } else {
        list.forEach((fdi, i) => {
            slots[i] = fdi;
        });
    }
    return slots;
}

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

/**
 * Caras de una pieza, con el camino SVG y el centro de cada zona.
 * Mesial hacia la línea media. Vestibular hacia afuera de la boca.
 *
 * @param {string} fdi
 * @param {boolean} lower
 * @returns {{surface: string, d: string, x: number, y: number}[]}
 */
export function faceLayout(fdi, lower) {
    const mesialRight = ["1", "4", "5", "8"].includes(String(fdi || "")[0]);
    return [
        { surface: lower ? "lingual" : "buccal", d: SLICES.top, x: 50, y: 33 },
        { surface: mesialRight ? "mesial" : "distal", d: SLICES.right, x: 68, y: 51 },
        { surface: lower ? "buccal" : "lingual", d: SLICES.bottom, x: 50, y: 69 },
        { surface: mesialRight ? "distal" : "mesial", d: SLICES.left, x: 32, y: 51 },
    ];
}
