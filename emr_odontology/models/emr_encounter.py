##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""La consulta odontológica.

Es un tipo de historia clínica más: delega los campos comunes en
emr.encounter y acá van el motivo, la evolución y las piezas que se
trabajaron en la visita.

Cada línea, al crearse o editarse, y la visita al cerrarse, actualizan el
odontograma del paciente. La línea dice cómo quedó esa pieza y esa cara.
Sacar una línea de la visita no borra la marca del mapa: el odontograma no
tiene el estado anterior para volver atrás. Lo que queda de historial es
esta atención.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EmrEncounterOdontology(models.Model):
    _name = "emr.encounter.odontology"
    _description = "Consulta odontológica"
    _inherit = "emr.encounter.mixin"
    _inherits = {"emr.encounter": "encounter_id"}

    reason = fields.Text("Motivo de consulta")
    notes = fields.Text("Evolución")
    line_ids = fields.One2many(
        "emr.encounter.odontology.line",
        "odontology_id",
        string="Tratamientos",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "encounter_type_id" in fields_list and not res.get("encounter_type_id"):
            res["encounter_type_id"] = self._default_encounter_type().id
        return res

    @api.model
    def _default_encounter_type(self):
        """El tipo se busca por modelo, igual que en la receta.

        Así el alta no depende de que el xmlid del dato siga llamándose igual.
        """
        tipo = self.env["emr.encounter.type"].search(
            [("model_name", "=", self._name)], limit=1
        )
        if not tipo:
            raise UserError(
                _("No está definido el tipo de historia clínica de odontología.")
            )
        return tipo

    @api.model_create_multi
    def create(self, vals_list):
        tipo = None
        for vals in vals_list:
            if not vals.get("encounter_type_id"):
                if tipo is None:
                    tipo = self._default_encounter_type()
                vals["encounter_type_id"] = tipo.id
        records = super().create(vals_list)
        records._sync_odontogram()
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("emr_odontogram_no_sync"):
            self._sync_odontogram()
        return res

    def action_close(self):
        # Otra vez, además de en cada escritura: cerrar es el momento en que
        # la visita queda como hecha, y el mapa tiene que reflejarla aunque
        # la última edición no haya pasado por write del hijo.
        self._sync_odontogram()
        return super().action_close()

    def _sync_odontogram(self):
        """Pisa en el odontograma cada pieza que esta visita menciona.

        El orden es el de la lista: si hay dos líneas para la misma pieza y
        la misma cara, queda la última. Una nota vacía no borra la nota que
        ya tenía el mapa —el clic del mapa crea líneas sin nota, y no tiene
        que limpiar lo que alguien escribió antes.
        """
        if self.env.context.get("emr_odontogram_no_sync"):
            return
        Odontogram = self.env["emr.odontogram"]
        Tooth = self.env["emr.odontogram.tooth"]
        for rec in self:
            if not rec.partner_id or not rec.active or not rec.encounter_id:
                continue
            chart = Odontogram._get_or_create(rec.partner_id)
            by_key = {(tooth.fdi, tooth.surface): tooth for tooth in chart.tooth_ids}
            lines = rec.line_ids.sorted(key=lambda line: (line.sequence, line.id))
            for line in lines:
                if not line.fdi or not line.surface:
                    continue
                vals = {
                    "condition": line.condition,
                    "status": line.status,
                    "last_encounter_id": rec.encounter_id.id,
                }
                if line.notes:
                    vals["notes"] = line.notes
                tooth = by_key.get((line.fdi, line.surface))
                if tooth:
                    same = (
                        tooth.condition == line.condition
                        and tooth.status == line.status
                        and tooth.last_encounter_id == rec.encounter_id
                        and (not line.notes or tooth.notes == line.notes)
                    )
                    if not same:
                        tooth.write(vals)
                else:
                    vals.update({
                        "odontogram_id": chart.id,
                        "fdi": line.fdi,
                        "surface": line.surface,
                    })
                    by_key[(line.fdi, line.surface)] = Tooth.create(vals)


class EmrEncounterOdontologyLine(models.Model):
    _name = "emr.encounter.odontology.line"
    _description = "Tratamiento de la consulta odontológica"
    _inherit = "emr.odontogram.mark"
    _order = "sequence, id"

    odontology_id = fields.Many2one(
        "emr.encounter.odontology",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_not_signed()
        records.mapped("odontology_id")._sync_odontogram()
        return records

    def write(self, vals):
        self._check_not_signed()
        res = super().write(vals)
        if not self.env.context.get("emr_odontogram_no_sync"):
            self.mapped("odontology_id")._sync_odontogram()
        return res

    def unlink(self):
        self._check_not_signed()
        parents = self.mapped("odontology_id")
        res = super().unlink()
        parents._sync_odontogram()
        return res

    def _check_not_signed(self):
        """La guarda del padre no alcanza para el renglón, igual que en la receta.

        Una atención firmada no se corrige: se le agrega un agregado. El mapa
        sí se puede seguir corrigiendo, porque es el estado actual y no esta
        visita.
        """
        if self.env.context.get("emr_allow_signed_edit"):
            return
        if any(line.odontology_id.state == "signed" for line in self):
            raise UserError(
                _(
                    "Esta consulta está firmada y sus tratamientos no se "
                    "pueden modificar."
                )
            )
