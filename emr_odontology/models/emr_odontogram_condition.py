##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Catálogo de estados del odontograma.

Sano, caries, corona y el resto no están fijos en el código: el nombre
y el color se editan en Configuración → Estados. El código técnico sí
queda fijo, porque es lo que se guarda en cada marca. Cambiarlo
rompería las piezas ya cargadas.
"""
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
_COLOR_RE = re.compile(r"^#[0-9a-f]{6}$")


class EmrOdontogramCondition(models.Model):
    _name = "emr.odontogram.condition"
    _description = "Estado del odontograma"
    _order = "sequence, id"
    _rec_name = "name"

    sequence = fields.Integer(default=10)
    code = fields.Char(
        string="Código",
        required=True,
        index=True,
        help="Clave técnica. No se cambia: es la que queda guardada en "
        "cada marca del odontograma.",
    )
    name = fields.Char(string="Nombre", required=True)
    color = fields.Char(
        string="Color",
        required=True,
        default="#cfd8dc",
        help="Hexadecimal de seis dígitos, como #fff59d.",
    )
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        "UNIQUE (code)",
        "Ese código de estado ya existe.",
    )

    @api.model
    def _normalize_vals(self, vals):
        if vals.get("code"):
            vals["code"] = vals["code"].strip().lower()
        if vals.get("color"):
            vals["color"] = vals["color"].strip().lower()
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalize_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        vals = self._normalize_vals(dict(vals))
        if "code" in vals:
            for rec in self:
                if vals["code"] != rec.code:
                    raise UserError(
                        _(
                            "El código técnico no se cambia: las marcas "
                            "ya guardadas lo usan."
                        )
                    )
            vals.pop("code")
        return super().write(vals)

    def unlink(self):
        Tooth = self.env["emr.odontogram.tooth"].sudo()
        Line = self.env["emr.encounter.odontology.line"].sudo()
        for cond in self:
            used = Tooth.search_count(
                [("condition", "=", cond.code)]
            ) or Line.search_count([("condition", "=", cond.code)])
            if used:
                raise UserError(
                    _(
                        "No se puede borrar «%s» porque hay piezas marcadas. "
                        "Archivalo para sacarlo de la leyenda.",
                        cond.name,
                    )
                )
        return super().unlink()

    @api.constrains("code", "color")
    def _check_code_and_color(self):
        for rec in self:
            if not _CODE_RE.match(rec.code or ""):
                raise ValidationError(
                    _(
                        "El código usa solo minúsculas, números y guion "
                        "bajo, y empieza con una letra."
                    )
                )
            if not _COLOR_RE.match(rec.color or ""):
                raise ValidationError(
                    _(
                        "El color tiene que ser un hexadecimal de 6 "
                        "dígitos, como #fff59d."
                    )
                )
