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

from .sale_order import BILLABLE_STATUSES, ODONTOLOGY_PRODUCT_NAMES


def _remove_sale_line(sale_line):
    """Saca del pedido la línea de una marca que ya no corresponde."""
    sale_line = sale_line.sudo()
    if sale_line.order_id.state in ("draft", "sent"):
        sale_line.unlink()
    elif sale_line.product_uom_qty:
        sale_line.product_uom_qty = 0


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

    def action_view_sale_order(self):
        """«Ver presupuesto»: el turno de esta visita, con las prácticas."""
        self.ensure_one()
        order = self.encounter_id.order_id
        if not order:
            raise UserError(_("Esta consulta no tiene un turno asociado."))
        # Antes de abrirlo, por si quedó alguna marca sin volcar.
        self._sync_sale_order_lines()
        return {
            "type": "ir.actions.act_window",
            "name": _("Presupuesto"),
            "res_model": "sale.order",
            "res_id": order.id,
            "view_mode": "form",
            "target": "current",
        }

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
        self._sync_sale_order_lines()

    def _sync_sale_order_lines(self):
        """Pone en el turno una línea por cada marca que es una práctica.

        Es idempotente: cada línea del pedido sabe de qué marca viene, y se
        actualiza en lugar de duplicarse. Si la marca deja de ser una
        práctica (vuelve a "Sano", por ejemplo) la línea se borra mientras el
        pedido es presupuesto, y queda en cantidad cero si ya está
        confirmado, porque Odoo no deja borrar líneas de una venta.

        Corre como superusuario: quien marca es el profesional, que no
        necesariamente tiene permisos de ventas, y lo que se escribe lo
        decide esta regla y no él.
        """
        SaleLine = self.env["sale.order.line"].sudo()
        for rec in self.sudo():
            order = rec.encounter_id.order_id
            if not order or order.state == "cancel" or order.locked:
                continue
            existing = SaleLine.search(
                [("odontology_line_id", "in", rec.line_ids.ids)]
            ) if rec.line_ids else SaleLine
            by_mark = {sol.odontology_line_id.id: sol for sol in existing}
            next_seq = max(order.order_line.mapped("sequence") or [10]) + 1
            for line in rec.line_ids.sorted(key=lambda l: (l.sequence, l.id)):
                sol = by_mark.get(line.id)
                if sol and sol.order_id != order:
                    continue
                product = line._odontology_product(order.company_id)
                if not product:
                    if sol:
                        _remove_sale_line(sol)
                    continue
                vals = {
                    "product_id": product.id,
                    "name": line._odontology_sale_line_name(),
                    "product_uom_qty": 1,
                }
                if sol:
                    changed = {
                        key: value
                        for key, value in vals.items()
                        if (sol[key].id if key == "product_id" else sol[key]) != value
                    }
                    if "product_id" in changed:
                        # El nombre se recalcula al cambiar el producto: se
                        # escribe de nuevo para que quede el de la marca.
                        changed["name"] = vals["name"]
                    if changed:
                        sol.write(changed)
                else:
                    vals.update({
                        "order_id": order.id,
                        "odontology_line_id": line.id,
                        "sequence": next_seq,
                    })
                    next_seq += 1
                    SaleLine.create(vals)


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
        for sale_line in self.env["sale.order.line"].sudo().search(
            [("odontology_line_id", "in", self.ids)]
        ):
            if sale_line.order_id.state != "cancel" and not sale_line.order_id.locked:
                _remove_sale_line(sale_line)
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

    def _odontology_product(self, company):
        """El producto de esta marca, o nada si la marca no es una práctica.

        Se usa el producto que tenga configurada la condición; si nadie lo
        configuró (o lo archivaron) se crea uno de servicio con el nombre de
        la práctica, para que la marca nunca se pierda del presupuesto.
        """
        self.ensure_one()
        if self.status not in BILLABLE_STATUSES:
            return self.env["product.product"]
        name = ODONTOLOGY_PRODUCT_NAMES.get(self.condition)
        if not name:
            return self.env["product.product"]
        Product = self.env["product.product"].sudo()
        product = Product.search(
            [
                ("odontology_condition", "=", self.condition),
                ("sale_ok", "=", True),
                ("company_id", "in", [False, company.id]),
            ],
            order="company_id, id",
            limit=1,
        )
        if not product:
            product = Product.create({
                "name": name,
                "type": "service",
                "sale_ok": True,
                "purchase_ok": False,
                "is_medical_procedure": True,
                "odontology_condition": self.condition,
            })
        return product

    def _odontology_sale_line_name(self):
        """"Caries distal pieza 14 (A tratar)", o "Endodoncia pieza 36"."""
        self.ensure_one()
        partes = [self.selection_label("condition")]
        if self.surface != "tooth":
            partes.append(self.selection_label("surface").lower())
        partes.append(_("pieza %s", self.fdi))
        name = " ".join(partes)
        status = self.selection_label("status")
        if status:
            name = f"{name} ({status})"
        if self.notes:
            name = f"{name}\n{self.notes}"
        return name

