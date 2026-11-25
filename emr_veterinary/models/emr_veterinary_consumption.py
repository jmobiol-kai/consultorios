##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class EmrVeterinaryConsumptionLine(models.Model):
    """Medicamento o insumo usado en la consulta.

    Al cerrar la atención, lo almacenable sale del depósito de la clínica y,
    si corresponde, se agrega al pedido del dueño para facturarlo.
    """

    _name = "emr.veterinary.consumption.line"
    _description = "Consumo de la consulta"
    _inherit = "emr.veterinary.signed.mixin"
    _order = "id"

    encounter_id = fields.Many2one(
        "emr.encounter.veterinary",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        required=True,
        domain="[('veterinary_kind', 'in', ('medicine', 'accessory', 'food', 'service'))]",
    )
    quantity = fields.Float("Cantidad", required=True, default=1.0, digits="Product Unit")
    product_uom_id = fields.Many2one(related="product_id.uom_id", string="Unidad")
    tracking = fields.Selection(related="product_id.tracking")
    lot_id = fields.Many2one(
        "stock.lot",
        string="Lote",
        domain="[('product_id', '=', product_id)]",
    )
    expiration_date = fields.Datetime(
        related="lot_id.expiration_date", string="Vencimiento"
    )
    to_invoice = fields.Boolean(
        "Facturar al dueño",
        default=True,
        help="Suma el producto al pedido del dueño. Si el turno ya estaba "
        "facturado, queda una factura en borrador con este importe.",
    )
    stock_move_id = fields.Many2one("stock.move", string="Movimiento", readonly=True, copy=False)
    sale_line_id = fields.Many2one(
        "sale.order.line", string="Línea de venta", readonly=True, copy=False
    )
    company_id = fields.Many2one(related="encounter_id.company_id", store=True)

    @api.depends(
        "product_id.display_name", "quantity", "lot_id.name", "expiration_date"
    )
    def _compute_display_name(self):
        for line in self:
            bits = [line.product_id.display_name or ""]
            if line.quantity:
                bits.append("x %s" % line.quantity)
            if line.lot_id:
                bits.append("lote %s" % line.lot_id.name)
            if line.expiration_date:
                bits.append(fields.Datetime.to_string(line.expiration_date)[:10])
            line.display_name = " · ".join(bit for bit in bits if bit)

    def _emr_vet_encounter(self):
        self.ensure_one()
        return self.encounter_id

    @api.constrains("product_id", "lot_id", "quantity")
    def _check_lot_and_qty(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("La cantidad tiene que ser mayor a cero."))
            if line.lot_id and line.lot_id.product_id != line.product_id:
                raise ValidationError(
                    _("El lote %(lot)s no es de %(product)s.",
                      lot=line.lot_id.name, product=line.product_id.display_name)
                )
            if line.product_id.tracking in ("lot", "serial") and not line.lot_id:
                raise ValidationError(
                    _("Hay que indicar el lote de %s.", line.product_id.display_name)
                )

    def _create_sale_line(self):
        self.ensure_one()
        order = self.encounter_id._consumption_order()
        line = self.env["sale.order.line"].sudo().with_company(order.company_id).with_context(
            skip_procurement=True
        ).create(
            {
                "order_id": order.id,
                "product_id": self.product_id.id,
                "product_uom_qty": self.quantity,
            }
        )
        if self.lot_id:
            extra = _("Lote %s", self.lot_id.name)
            if self.expiration_date:
                extra = "%s · vto %s" % (
                    extra, fields.Datetime.to_string(self.expiration_date)[:10]
                )
            line.name = "%s\n%s" % (line.name or self.product_id.display_name, extra)
        self.sale_line_id = line.id
        return line

    def _create_stock_move(self):
        """Sale del depósito de la clínica hacia el cliente (el dueño)."""
        self.ensure_one()
        product = self.product_id
        if not product.is_storable:
            return self.env["stock.move"]
        company = self.encounter_id.company_id
        warehouse = self.env["stock.warehouse"].sudo().search(
            [("company_id", "=", company.id)], limit=1
        )
        if not warehouse:
            raise UserError(
                _("%s no tiene depósito.", company.display_name)
            )
        customer = self.env.ref("stock.stock_location_customers")
        move = self.env["stock.move"].sudo().create(
            {
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": self.quantity,
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": customer.id,
                "company_id": company.id,
                "origin": self.encounter_id.display_name,
                "partner_id": self.encounter_id.partner_id.id,
                "sale_line_id": self.sale_line_id.id or False,
            }
        )
        move._action_confirm()
        move._action_assign()
        if not move.move_line_ids:
            self.env["stock.move.line"].sudo().create(
                {
                    "move_id": move.id,
                    "product_id": product.id,
                    "product_uom_id": product.uom_id.id,
                    "location_id": move.location_id.id,
                    "location_dest_id": move.location_dest_id.id,
                    "lot_id": self.lot_id.id or False,
                    "quantity": self.quantity,
                    "picked": True,
                    "company_id": company.id,
                }
            )
        else:
            vals = {"quantity": self.quantity, "picked": True}
            if self.lot_id:
                vals["lot_id"] = self.lot_id.id
            move.move_line_ids.sudo().write(vals)
        move.picked = True
        move._action_done()
        self.stock_move_id = move.id
        return move
