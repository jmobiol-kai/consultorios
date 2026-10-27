##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EmrSlotFilter(models.TransientModel):
    """Ver una agenda acotada, agrupada por día.

    La grilla completa mezcla a todos y en una clínica con veinte
    profesionales eso no se lee. Acotarla por profesional responde "¿cuándo
    tiene lugar el doctor?"; acotarla por locación responde "¿cuándo está
    libre la sala?". Son la misma vista con distinta pregunta, así que van en
    un solo asistente en vez de dos botones que hacen casi lo mismo.

    Se podría hacer con el filtro y el agrupar de la búsqueda, pero son tres
    clics y hay que acordarse de los dos. Acá es un botón.
    """

    _name = "emr.slot.filter"
    _description = "Ver una agenda filtrada"

    practitioner_id = fields.Many2one(
        "res.partner",
        string="Profesional",
        # Solo los que agendan: los del padrón no tienen huecos que mirar.
        domain=[("is_practitioner", "=", True), ("scheduling_method", "!=", False)],
        context={"default_is_practitioner": True},
    )
    # Los dos ejes son opcionales y se combinan: todo lo de un profesional,
    # todo lo que pasa en una sala, o ese profesional en esa sala.
    location_id = fields.Many2one("emr.location", string="Locación")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "practitioner_id" in fields_list and not res.get("practitioner_id"):
            # Si quien mira es un profesional, su agenda es la que quiere ver.
            propio = self.env["res.partner"].search(
                [
                    ("is_practitioner", "=", True),
                    ("scheduling_method", "!=", False),
                    ("user_ids", "in", self.env.user.ids),
                ],
                limit=1,
            )
            if propio:
                res["practitioner_id"] = propio.id
        return res

    def action_filter(self):
        """Arranca en los próximos siete días.

        La agenda entera de un profesional son miles de huecos y no es lo que
        nadie quiere ver primero. La semana sí, y desde ahí se navega.
        """
        self.ensure_one()
        if not self.practitioner_id and not self.location_id:
            raise UserError(
                _("Elegí un profesional, una locación, o los dos.")
            )
        return self.env["emr.slot"]._emr_agenda_action(
            self.practitioner_id, self.location_id
        )
