##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""El odontograma: el estado actual de la boca, uno por paciente.

La visita (`emr.encounter.odontology`) anota lo que se hizo ese día y, al
guardarse o cerrarse, pisa acá la pieza y la cara que tocó. Este registro no
es el historial —el historial son las atenciones— y por eso se puede corregir
a mano: una pieza marcada mal se arregla en el mapa, sin reescribir la visita
que ya quedó firmada.

La notación es FDI. Permanentes: 11-18, 21-28, 31-38, 41-48. Temporarias:
51-55, 61-65, 71-75, 81-85. Las temporarias no se crean solas; aparecen
cuando alguien las marca.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


# Orden anatómico, de la derecha del paciente a la izquierda, arriba y abajo.
# El mapa lo dibuja igual; la selección del formulario usa la misma lista.
PERMANENT_QUADRANTS = (
    ("18", "17", "16", "15", "14", "13", "12", "11"),
    ("21", "22", "23", "24", "25", "26", "27", "28"),
    ("48", "47", "46", "45", "44", "43", "42", "41"),
    ("31", "32", "33", "34", "35", "36", "37", "38"),
)
DECIDUOUS_QUADRANTS = (
    ("55", "54", "53", "52", "51"),
    ("61", "62", "63", "64", "65"),
    ("85", "84", "83", "82", "81"),
    ("71", "72", "73", "74", "75"),
)


def _fdi_selection():
    codes = []
    for quadrant in PERMANENT_QUADRANTS + DECIDUOUS_QUADRANTS:
        codes.extend(quadrant)
    return tuple((code, code) for code in codes)


FDI_SELECTION = _fdi_selection()

# "Pieza" es la pieza entera, no una cara. Oclusal incluye el borde incisal;
# palatino incluye lingual. Un solo valor alcanza para el mapa.
SURFACE_SELECTION = [
    ("tooth", "Pieza"),
    ("mesial", "Mesial"),
    ("distal", "Distal"),
    ("occlusal", "Oclusal"),
    ("buccal", "Vestibular"),
    ("lingual", "Palatino"),
]
CONDITION_SELECTION = [
    ("sound", "Sano"),
    ("caries", "Caries"),
    ("restoration", "Obturación"),
    ("crown", "Corona"),
    ("endodontics", "Endodoncia"),
    ("implant", "Implante"),
    ("fracture", "Fractura"),
    ("extraction", "Extracción indicada"),
    ("missing", "Ausente"),
    ("prosthesis", "Prótesis"),
    ("sealant", "Sellador"),
]
STATUS_SELECTION = [
    ("present", "Presente"),
    ("pending", "A tratar"),
    ("treated", "Tratado"),
    ("missing", "Ausente"),
    ("unerupted", "No erupcionado"),
]


class EmrOdontogramMark(models.AbstractModel):
    """Los campos de una marca, compartidos por el mapa y por la visita.

    Son los mismos a propósito: la visita vuelca la línea al odontograma
    campo por campo, y el mapa pinta las dos listas con el mismo widget.
    """

    _name = "emr.odontogram.mark"
    _description = "Marca de odontograma"
    _rec_name = "fdi"

    fdi = fields.Selection(FDI_SELECTION, string="Pieza (FDI)", required=True)
    surface = fields.Selection(
        SURFACE_SELECTION, string="Cara", required=True, default="tooth"
    )
    condition = fields.Selection(
        selection="_selection_condition",
        string="Condición",
        required=True,
        default="sound",
    )
    status = fields.Selection(
        selection="_selection_status",
        string="Estado",
        required=True,
        default="present",
    )
    notes = fields.Text("Notas")

    @api.model
    def _selection_condition(self):
        """Nombre visible de cada estado, tomado de Configuración.

        El valor guardado sigue siendo el código (`crown`, `caries`, …).
        Si el catálogo todavía no está (instalación) se usan los nombres
        de fábrica, que coinciden con los datos iniciales.
        """
        fallback = list(CONDITION_SELECTION)
        try:
            rows = (
                self.env["emr.odontogram.condition"]
                .sudo()
                .with_context(active_test=False)
                .search([])
            )
        except Exception:
            return fallback
        if not rows:
            return fallback
        return [(row.code, row.name) for row in rows]

    @api.model
    def _selection_status(self):
        """Nombre visible de cada situación, tomado de Configuración.

        El valor guardado sigue siendo el código (`pending`, `treated`,
        …). El presupuesto compara esos códigos, no el nombre. Si el
        catálogo todavía no está (instalación) se usan los nombres de
        fábrica, que coinciden con los datos iniciales.
        """
        fallback = list(STATUS_SELECTION)
        try:
            rows = (
                self.env["emr.odontogram.status"]
                .sudo()
                .with_context(active_test=False)
                .search([])
            )
        except Exception:
            return fallback
        if not rows:
            return fallback
        return [(row.code, row.name) for row in rows]

    display_name = fields.Char(compute="_compute_display_name")

    def selection_label(self, field_name):
        self.ensure_one()
        field = self._fields[field_name]
        return dict(field._description_selection(self.env)).get(self[field_name]) or ""

    @api.depends("fdi", "surface", "condition", "status", "notes")
    def _compute_display_name(self):
        for mark in self:
            partes = [
                mark.fdi,
                mark.selection_label("surface"),
                mark.selection_label("condition"),
                mark.selection_label("status"),
            ]
            partes = [p for p in partes if p]
            if mark.notes:
                partes.append(mark.notes[:80])
            mark.display_name = " · ".join(partes)


class EmrOdontogram(models.Model):
    _name = "emr.odontogram"
    _description = "Odontograma"
    _order = "id desc"

    partner_id = fields.Many2one(
        "res.partner",
        string="Paciente",
        required=True,
        index=True,
        ondelete="restrict",
        domain=[("is_patient", "=", True)],
        context={"default_is_patient": True, "show_vat": True},
    )
    tooth_ids = fields.One2many(
        "emr.odontogram.tooth", "odontogram_id", string="Piezas"
    )

    display_name = fields.Char(compute="_compute_display_name")

    _partner_uniq = models.Constraint(
        "UNIQUE (partner_id)",
        "El paciente ya tiene un odontograma.",
    )

    @api.depends("partner_id")
    def _compute_display_name(self):
        for chart in self:
            chart.display_name = _("Odontograma de %s", chart.partner_id.name or "")

    @api.constrains("partner_id")
    def _check_patient(self):
        for chart in self:
            if chart.partner_id and not chart.partner_id.is_patient:
                raise ValidationError(
                    _("El odontograma es de un paciente.")
                )

    @api.model
    def _get_or_create(self, partner):
        """El odontograma del paciente, creándolo si todavía no existe."""
        chart = self.search([("partner_id", "=", partner.id)], limit=1)
        if not chart:
            chart = self.create({"partner_id": partner.id})
        return chart

    def action_odontology_walkin(self):
        """«Atender ahora» desde el mapa: abre una visita con turno.

        Lo que se marca directo en este mapa no se cobra —no hay visita—;
        para que la práctica llegue al presupuesto se anota en la consulta.
        """
        self.ensure_one()
        return self.partner_id.action_odontology_walkin()

    def copy(self, default=None):
        raise UserError(
            _("El odontograma es uno por paciente y no se duplica.")
        )


class EmrOdontogramTooth(models.Model):
    _name = "emr.odontogram.tooth"
    _description = "Pieza del odontograma"
    _inherit = "emr.odontogram.mark"
    _order = "fdi, surface, id"

    odontogram_id = fields.Many2one(
        "emr.odontogram",
        required=True,
        ondelete="cascade",
        index=True,
    )
    last_encounter_id = fields.Many2one(
        "emr.encounter",
        string="Última atención",
        ondelete="set null",
        help="La visita que dejó la pieza así. No es el historial: el "
        "historial son las atenciones, y una corrección hecha en el mapa "
        "no las reescribe.",
    )

    _tooth_surface_uniq = models.Constraint(
        "UNIQUE (odontogram_id, fdi, surface)",
        "Esa pieza y esa cara ya están en el odontograma.",
    )
