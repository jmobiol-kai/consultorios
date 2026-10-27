##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EmrEncounterAddendum(models.Model):
    """Un agregado a una historia clínica.

    Es la vía prevista para sumar información a una atención ya firmada: deja
    el original intacto y suma lo nuevo con su autor y su fecha. Así no hay
    valor anterior que rastrear, porque no se pisa nada.
    """

    _name = "emr.encounter.addendum"
    _description = "Agregado a la historia clínica"
    _order = "create_date desc, id desc"

    encounter_id = fields.Many2one(
        "emr.encounter",
        string="Atención",
        required=True,
        index=True,
        ondelete="cascade",
    )
    body = fields.Html("Contenido", required=True, sanitize=True)
    author_id = fields.Many2one(
        "res.users", string="Autor", required=True, readonly=True,
        default=lambda self: self.env.user,
    )
    date = fields.Datetime(
        "Fecha", required=True, readonly=True, default=fields.Datetime.now
    )

    def write(self, vals):
        """Un agregado tampoco se edita: si hay que corregirlo, se agrega otro."""
        raise UserError(
            _("Un agregado no se modifica. Si hay que corregirlo, sumá uno nuevo.")
        )

    def unlink(self):
        raise UserError(_("Un agregado no se borra."))
