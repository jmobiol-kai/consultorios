##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain

from odoo.addons.emr.models.calendar_label import appointment_calendar_lines

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    pet_id = fields.Many2one(
        "emr.pet",
        string="Mascota",
        index=True,
        ondelete="restrict",
        tracking=False,
    )

    @api.depends(
        "partner_id.name",
        "name",
        "is_appointment",
        "sale_order_template_id.name",
        "order_line.product_id.name",
        "order_line.product_id.is_medical_procedure",
        "pet_id.name",
    )
    def _compute_appointment_calendar_title(self):
        super()._compute_appointment_calendar_title()
        for order in self.filtered(lambda item: item.is_appointment and item.pet_id):
            title, subtitle = appointment_calendar_lines(
                order.pet_id.name,
                order.appointment_calendar_subtitle,
            )
            order.appointment_calendar_title = title
            order.appointment_calendar_subtitle = subtitle

    def _emr_appointment_partner_is_valid(self):
        self.ensure_one()
        if self.pet_id:
            return bool(self.partner_id)
        return super()._emr_appointment_partner_is_valid()

    @api.onchange("pet_id")
    def _onchange_vet_pet_id(self):
        if not self.pet_id:
            return
        self.partner_id = self.pet_id.owner_id
        pricelist = self.pet_id.owner_id.property_product_pricelist
        if pricelist:
            self.pricelist_id = pricelist

    def _onchange_partner_id_insurer_pricelist(self):
        if self.pet_id:
            pricelist = self.partner_id.property_product_pricelist
            if pricelist:
                self.pricelist_id = pricelist
            return
        return super()._onchange_partner_id_insurer_pricelist()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            pet_id = vals.get("pet_id")
            if not pet_id:
                continue
            pet = self.env["emr.pet"].browse(pet_id)
            if vals.get("is_appointment") and pet.deceased:
                raise UserError(
                    _(
                        "No se puede agendar un turno para %(name)s porque figura como fallecido.",
                        name=pet.name,
                    )
                )
            if pet.owner_id:
                vals["partner_id"] = pet.owner_id.id
        return super().create(vals_list)

    def _open_encounter(self):
        self.ensure_one()
        if self.pet_id and not self.encounter_id:
            return super(
                SaleOrder, self.with_context(default_pet_id=self.pet_id.id)
            )._open_encounter()
        return super()._open_encounter()

    def _get_product_catalog_domain(self):
        domain = super()._get_product_catalog_domain()
        if self.env.context.get("emr_veterinary_counter_sale"):
            domain &= Domain(
                "veterinary_kind", "in", ("medicine", "accessory", "food")
            )
        return domain

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            try:
                with self.env.cr.savepoint():
                    order._emr_veterinary_auto_validate_delivery()
            except Exception as err:
                _logger.exception(
                    "No se pudo validar la entrega de %s", order.display_name
                )
                order.message_post(body=_(
                    "No se pudo validar la entrega automáticamente. "
                    "Quedó pendiente. %(error)s",
                    error=err,
                ))
        return res

    def _emr_veterinary_auto_validate_delivery(self):
        """Valida la entrega saliente si todo lo almacenable está reservado.

        Un pedido del sitio no se toca: se retira después. Si falta stock
        para alguna línea, no se valida nada. Un lote vencido o ausente
        tampoco. El error lo absorbe ``action_confirm``.
        """
        self.ensure_one()
        if not self.company_id.emr_veterinary_auto_validate_delivery:
            return
        if "website_id" in self._fields and self.website_id:
            return
        pickings = self._emr_veterinary_outgoing_pickings()
        if not pickings:
            return
        if not all(self._emr_veterinary_picking_fully_reserved(p) for p in pickings):
            return
        if not all(self._emr_veterinary_picking_lots_ok(p) for p in pickings):
            names = ", ".join(pickings.mapped("name"))
            _logger.info(
                "No se valida la entrega de %s: lote vencido o sin lote (%s)",
                self.display_name,
                names,
            )
            self.message_post(body=_(
                "No se validó la entrega %(pickings)s: hay un lote vencido o falta el lote.",
                pickings=names,
            ))
            return
        for picking in pickings:
            moves = picking.move_ids.filtered(lambda move: move.state != "cancel")
            for move in moves:
                move.quantity = move.product_uom_qty
                move.picked = True
            # Odoo 19 no tiene asistente de transferencia inmediata.
            # skip_backorder, skip_expired y skip_sms evitan los que sí hay.
            result = picking.with_context(
                skip_backorder=True,
                skip_immediate=True,
                skip_expired=True,
                skip_sms=True,
            ).button_validate()
            # Un asistente de impresión puede devolver una acción aunque
            # la entrega ya quedó hecha. Si no quedó hecha, se deshace.
            if picking.state != "done":
                raise UserError(_(
                    "La entrega %(name)s no se pudo validar.",
                    name=picking.display_name,
                ))
            if result is not True:
                _logger.info(
                    "La entrega %s quedó validada y Odoo devolvió una acción",
                    picking.display_name,
                )

    def _emr_veterinary_outgoing_pickings(self):
        self.ensure_one()
        return self.picking_ids.filtered(
            lambda picking: picking.state not in ("done", "cancel")
            and picking.picking_type_code == "outgoing"
            and picking.move_ids.filtered(
                lambda move: move.state != "cancel" and move.product_id.is_storable
            )
        )

    def _emr_veterinary_picking_fully_reserved(self, picking):
        """Listo de verdad: cada línea almacenable está reservada por completo.

        En política «lo antes posible» el picking figura assigned con que
        una sola línea tenga stock. Eso no alcanza para validar solo.
        """
        moves = picking.move_ids.filtered(
            lambda move: move.state != "cancel" and move.product_id.is_storable
        )
        return bool(moves) and all(move.state == "assigned" for move in moves)

    def _emr_veterinary_picking_lots_ok(self, picking):
        """Usa los lotes que ya reservó la agenda FEFO. No elige otros.

        Si el producto lleva lote y la reserva no dejó uno, o el que dejó
        está vencido, esta entrega no se valida.
        """
        now = fields.Datetime.now()
        moves = picking.move_ids.filtered(
            lambda move: move.state != "cancel"
            and move.product_id.is_storable
            and move.product_id.tracking in ("lot", "serial")
        )
        for move in moves:
            lines = move.move_line_ids
            if not lines or any(not line.lot_id for line in lines):
                return False
            for line in lines:
                expiration = line.lot_id.expiration_date
                if expiration and expiration <= now:
                    return False
        return True
