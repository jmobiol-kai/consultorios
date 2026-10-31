##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Catálogo de situaciones de la marca (la columna Estado).

Presente, a tratar, tratado, ausente y no erupcionado no están fijos
en el código: el nombre se edita en Configuración → Estados de la
marca. El código técnico sí queda fijo, porque es lo que se guarda en
cada marca y lo que el presupuesto reconoce.

`pending` y `treated` van al turno aunque se les cambie el nombre.
Renombrar «A tratar» no deja de cobrarlo, y renombrar «Presente» no
lo hace cobrable.
"""
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .emr_odontogram import STATUS_SELECTION
from .sale_order import BILLABLE_STATUSES

_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
# Los de fábrica no se borran: la leyenda los asigna por código
# (caries → pending) y el presupuesto distingue por el mismo código.
FACTORY_STATUS_CODES = frozenset(code for code, _label in STATUS_SELECTION)


class EmrOdontogramStatus(models.Model):
    _name = "emr.odontogram.status"
    _description = "Estado de la marca"
    _order = "sequence, id"
    _rec_name = "name"

    sequence = fields.Integer(default=10)
    code = fields.Char(
        string="Código",
        required=True,
        index=True,
        help="Clave técnica. No se cambia: es la que queda guardada en "
        "cada marca. pending y treated son las que van al presupuesto.",
    )
    name = fields.Char(string="Nombre", required=True)
    active = fields.Boolean(default=True)
    billable = fields.Boolean(
        string="Presupuesto",
        compute="_compute_billable",
        help="Va al presupuesto del turno. Lo decide el código "
        "(pending y treated), no el nombre.",
    )

    _code_uniq = models.Constraint(
        "UNIQUE (code)",
        "Ese código de estado de la marca ya existe.",
    )

    @api.depends("code")
    def _compute_billable(self):
        for rec in self:
            rec.billable = rec.code in BILLABLE_STATUSES

    @api.model
    def _normalize_vals(self, vals):
        if vals.get("code"):
            vals["code"] = vals["code"].strip().lower()
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
                            "ya guardadas y el presupuesto lo usan."
                        )
                    )
            vals.pop("code")
        return super().write(vals)

    def unlink(self):
        Tooth = self.env["emr.odontogram.tooth"].sudo()
        Line = self.env["emr.encounter.odontology.line"].sudo()
        for rec in self:
            if rec.code in FACTORY_STATUS_CODES:
                raise UserError(
                    _(
                        "«%s» viene con el odontograma. Cambiá el nombre "
                        "si hace falta; el código lo usan las marcas y "
                        "el presupuesto.",
                        rec.name,
                    )
                )
            used = Tooth.search_count(
                [("status", "=", rec.code)]
            ) or Line.search_count([("status", "=", rec.code)])
            if used:
                raise UserError(
                    _(
                        "No se puede borrar «%s» porque hay piezas marcadas. "
                        "Archivalo para esconderlo de este listado.",
                        rec.name,
                    )
                )
        return super().unlink()

    @api.constrains("code")
    def _check_code(self):
        for rec in self:
            if not _CODE_RE.match(rec.code or ""):
                raise ValidationError(
                    _(
                        "El código usa solo minúsculas, números y guion "
                        "bajo, y empieza con una letra."
                    )
                )
