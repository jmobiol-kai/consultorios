/** @odoo-module **/

/**
 * Cuándo el formulario de una atención no se edita.
 *
 * `draft` es la visita en curso (Atender ahora, o una que sigue en
 * elaboración). Cerrada y firmada ya ocurrieron. La tarjeta de la
 * historia pide solo lectura aunque el estado haya quedado en
 * elaboración: se abre para consultar, no para corregir.
 *
 * @param {string | false | null | undefined} state
 * @param {boolean} historyReadonly
 * @returns {boolean}
 */
export function encounterFormMustBeReadonly(state, historyReadonly) {
    if (historyReadonly) {
        return true;
    }
    return Boolean(state) && state !== "draft";
}
