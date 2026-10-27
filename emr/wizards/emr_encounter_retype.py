##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EmrEncounterRetype(models.TransientModel):
    """Registrar la atención en otro tipo de historia clínica.

    Con herencia por delegación una atención no cambia de tipo: cada tipo es
    un modelo propio con sus campos. Así que esto no convierte nada — crea la
    historia del tipo correcto con el mismo encabezado y descarta la anterior.

    Es el caso de siempre: se apretó Atender, se abrió lo que dice la práctica
    del turno, y resulta que hay que registrar otra cosa.
    """

    _name = "emr.encounter.retype"
    _description = "Cambiar el tipo de historia clínica"

    encounter_id = fields.Many2one(
        "emr.encounter", string="Atención", required=True, readonly=True
    )
    partner_id = fields.Many2one(
        "res.partner", string="Paciente", related="encounter_id.partner_id"
    )
    current_type_id = fields.Many2one(
        "emr.encounter.type",
        string="Tipo actual",
        related="encounter_id.encounter_type_id",
    )
    encounter_type_id = fields.Many2one(
        "emr.encounter.type", string="Nuevo tipo", required=True
    )

    @api.constrains("encounter_type_id", "current_type_id")
    def _check_different(self):
        for wiz in self:
            if wiz.encounter_type_id == wiz.current_type_id:
                raise UserError(_("Es el mismo tipo que ya tiene."))

    def action_retype(self):
        self.ensure_one()
        old = self.encounter_id

        # Solo mientras está en elaboración: una historia cerrada o firmada es
        # un registro clínico, y eso no se reemplaza — se anula y se hace otra.
        if old.state != "draft":
            raise UserError(
                _(
                    "Esta historia clínica ya está cerrada. Para registrar otra "
                    "cosa hay que anularla y hacer una nueva."
                )
            )

        order = old.order_id
        new = self.env[self.encounter_type_id.model_name].create(
            {
                "partner_id": old.partner_id.id,
                "practitioner_id": old.practitioner_id.id,
                "date": old.date,
                "order_id": order.id or False,
                "location_id": old.location_id.id or False,
                "company_id": old.company_id.id,
                "encounter_type_id": self.encounter_type_id.id,
                "diagnosis_ids": [(6, 0, old.diagnosis_ids.ids)],
            }
        )
        # Se archiva en vez de borrarse. Borrar el registro que el usuario
        # tiene abierto deja al cliente navegando hacia algo que ya no existe,
        # y además en un registro clínico conviene el rastro de que se abrió
        # un tipo y se cambió por otro.
        old.with_context(emr_allow_signed_edit=True).write(
            {"active": False, "order_id": False}
        )
        if order:
            order.encounter_id = new.encounter_id

        # target "main" y no "current": al cerrarse el diálogo, el cliente
        # intentaría recargar el formulario del registro que se acaba de
        # borrar. Reemplazar el historial de navegación lo saca de en medio.
        return {
            "type": "ir.actions.act_window",
            "res_model": new._name,
            "res_id": new.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "main",
        }
