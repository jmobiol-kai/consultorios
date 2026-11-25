##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EmrPet(models.Model):
    """La mascota es el paciente. El dueño es quien paga.

    No es un res.partner. El partner del turno y de la historia clínica es el
    dueño, porque emr factura y lista por partner; la mascota vive al lado,
    y la historia se mira desde acá.
    """

    _name = "emr.pet"
    _description = "Mascota"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name, id"
    _rec_names_search = ["name", "microchip"]

    name = fields.Char(required=True, tracking=True)
    species_id = fields.Many2one(
        "emr.pet.species", string="Especie", required=True, ondelete="restrict", index=True
    )
    breed_id = fields.Many2one(
        "emr.pet.breed",
        string="Raza",
        ondelete="restrict",
        domain="[('species_id', '=', species_id)]",
    )
    sex = fields.Selection(
        [
            ("male", "Macho"),
            ("female", "Hembra"),
            ("unknown", "Sin especificar"),
        ],
        string="Sexo",
        default="unknown",
        required=True,
    )
    birth_date = fields.Date("Fecha de nacimiento")
    age = fields.Char("Edad", compute="_compute_age")
    color = fields.Char("Color")
    image_1920 = fields.Image("Foto", max_width=1920, max_height=1920)
    microchip = fields.Char("Microchip", index=True, copy=False)
    neutered = fields.Boolean("Castrado")
    owner_id = fields.Many2one(
        "res.partner",
        string="Dueño",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        help="Quien paga. No es el paciente: el paciente es esta mascota.",
    )
    deceased = fields.Boolean("Fallecido", tracking=True)
    deceased_date = fields.Date("Fecha de fallecimiento")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    weight_ids = fields.One2many("emr.pet.weight", "pet_id", string="Historial de peso")
    prevention_ids = fields.One2many(
        "emr.pet.prevention", "pet_id", string="Vacunas y desparasitación"
    )
    encounter_ids = fields.One2many("emr.encounter", "pet_id", string="Atenciones")
    encounter_count = fields.Integer(compute="_compute_encounter_count")

    @api.constrains("microchip")
    def _check_microchip_unique(self):
        for pet in self.filtered("microchip"):
            duplicate = self.search(
                [("microchip", "=", pet.microchip), ("id", "!=", pet.id)], limit=1
            )
            if duplicate:
                raise ValidationError(
                    _("Ya hay una mascota con el microchip %s.", pet.microchip)
                )

    @api.depends("name", "species_id.name", "owner_id.name")
    def _compute_display_name(self):
        for pet in self:
            bits = [pet.name or ""]
            if pet.species_id:
                bits.append(pet.species_id.name)
            if pet.owner_id:
                bits.append(pet.owner_id.name)
            pet.display_name = " · ".join(bits)

    @api.depends("birth_date")
    def _compute_age(self):
        today = fields.Date.context_today(self)
        for pet in self:
            pet.age = self._format_age(pet.birth_date, today)

    @api.depends("encounter_ids")
    def _compute_encounter_count(self):
        for pet in self:
            pet.encounter_count = len(pet.encounter_ids)

    @api.model
    def _format_age(self, birth_date, today):
        if not birth_date or birth_date > today:
            return ""
        years = today.year - birth_date.year
        months = today.month - birth_date.month
        if today.day < birth_date.day:
            months -= 1
        if months < 0:
            years -= 1
            months += 12
        parts = []
        if years:
            parts.append(
                _("%(count)s año", count=years)
                if years == 1
                else _("%(count)s años", count=years)
            )
        if months or not years:
            parts.append(
                _("%(count)s mes", count=months)
                if months == 1
                else _("%(count)s meses", count=months)
            )
        return " y ".join(parts)

    @api.onchange("species_id")
    def _onchange_species_id(self):
        if self.breed_id and self.breed_id.species_id != self.species_id:
            self.breed_id = False

    @api.onchange("deceased")
    def _onchange_deceased(self):
        if self.deceased and not self.deceased_date:
            self.deceased_date = fields.Date.context_today(self)
        if not self.deceased:
            self.deceased_date = False

    @api.constrains("breed_id", "species_id")
    def _check_breed_species(self):
        for pet in self:
            if pet.breed_id and pet.breed_id.species_id != pet.species_id:
                raise ValidationError(
                    _(
                        "La raza %(breed)s no es de la especie %(species)s.",
                        breed=pet.breed_id.name,
                        species=pet.species_id.name,
                    )
                )

    def _reminder_user(self):
        """A quién le cae el recordatorio de la próxima dosis.

        El profesional de la última atención, si tiene usuario. Si no, alguien
        de administración: el cron no puede dejar la actividad sin destinatario.
        """
        self.ensure_one()
        encounter = self.env["emr.encounter"].search(
            [
                ("pet_id", "=", self.id),
                ("practitioner_id.user_ids", "!=", False),
            ],
            order="date desc, id desc",
            limit=1,
        )
        if encounter:
            return encounter.practitioner_id.user_ids[:1]
        managers = self.env.ref("emr.group_emr_manager").all_user_ids[:1]
        return managers or self.env.user

    def action_open_encounters(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Historia clínica"),
            "res_model": "emr.encounter.veterinary",
            "view_mode": "list,form",
            "domain": [("pet_id", "=", self.id)],
            "context": {"default_pet_id": self.id},
        }

    def action_print_history(self):
        self.ensure_one()
        return self.env.ref("emr_veterinary.action_report_pet_history").report_action(self)

    @api.model
    def get_history_entries(self, pet_id, exclude_id=None, limit=20):
        """El panel de historia, filtrado a esta mascota.

        El partner de la atención es el dueño. Sin el filtro, el costado
        mezclaría todos los animales de esa persona.
        """
        pet = self.browse(pet_id).exists()
        if not pet or not pet.owner_id:
            return []
        return self.env["emr.encounter"].with_context(
            emr_pet_id=pet.id
        ).get_patient_history(pet.owner_id.id, exclude_id=exclude_id, limit=limit)
