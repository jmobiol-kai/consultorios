##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, models
from odoo.exceptions import UserError


class EmrVeterinarySignedMixin(models.AbstractModel):
    """Una línea colgada de una historia firmada no se toca.

    La guarda del encounter no alcanza: estas líneas son otro modelo, y
    escribirlas no pasa por emr.encounter.
    """

    _name = "emr.veterinary.signed.mixin"
    _description = "Bloqueo de líneas al firmar"

    # Campos operativos que el cron puede escribir igual (el recordatorio).
    _emr_vet_signed_ok = set()

    def _emr_vet_encounter(self):
        self.ensure_one()
        return self.env["emr.encounter"]

    def _emr_vet_check_not_signed(self):
        if self.env.context.get("emr_allow_signed_edit"):
            return
        for rec in self:
            encounter = rec._emr_vet_encounter()
            if encounter and encounter.state == "signed":
                raise UserError(
                    _(
                        "Esta historia clínica está firmada y no se puede "
                        "modificar. Para sumar información, agregá un agregado."
                    )
                )

    def _signed_write_is_allowed(self, vals):
        allowed = set(getattr(type(self), "_emr_vet_signed_ok", set()))
        return bool(allowed) and set(vals) <= allowed

    def write(self, vals):
        if not self._signed_write_is_allowed(vals):
            self._emr_vet_check_not_signed()
        return super().write(vals)

    def unlink(self):
        self._emr_vet_check_not_signed()
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._emr_vet_check_not_signed()
        return records
