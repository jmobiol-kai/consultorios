##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models, tools


class EmrVeterinaryMovement(models.Model):
    """Lo que pasó en la clínica, en una sola lista de solo lectura.

    Una fila por consulta veterinaria y una fila por pedido de venta que
    tenga medicamento, accesorio o alimento. El pedido de un turno entra
    una sola vez, aunque tenga varias líneas: no se duplica con otra fila
    de venta. Si ese pedido no lleva ninguno de esos productos, el dinero
    queda en la consulta y no hay una venta aparte.
    """

    _name = "emr.veterinary.movement"
    _description = "Movimiento del día"
    _auto = False
    _order = "date desc, id desc"
    _rec_name = "name"

    name = fields.Char("Documento", readonly=True)
    move_type = fields.Selection(
        [("consulta", "Consulta"), ("venta", "Venta")],
        string="Tipo",
        readonly=True,
    )
    date = fields.Datetime("Fecha", readonly=True)
    pet_id = fields.Many2one("emr.pet", string="Mascota", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Dueño", readonly=True)
    practitioner_id = fields.Many2one(
        "res.partner", string="Profesional", readonly=True
    )
    amount_total = fields.Monetary("Total", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    state_label = fields.Char("Estado", readonly=True)
    res_model = fields.Char(readonly=True)
    res_id = fields.Integer(readonly=True)
    company_id = fields.Many2one("res.company", string="Compañía", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                WITH retail_order AS (
                    SELECT DISTINCT sol.order_id AS order_id
                      FROM sale_order_line sol
                      JOIN product_product pp ON pp.id = sol.product_id
                      JOIN product_template pt ON pt.id = pp.product_tmpl_id
                     WHERE pt.veterinary_kind IN ('medicine', 'accessory', 'food')
                       AND sol.display_type IS NULL
                )
                SELECT
                    e.id AS id,
                    'consulta'::varchar AS move_type,
                    e.date AS date,
                    e.pet_id AS pet_id,
                    e.partner_id AS partner_id,
                    e.practitioner_id AS practitioner_id,
                    CASE
                        WHEN retail.order_id IS NULL THEN so.amount_total
                        ELSE NULL
                    END AS amount_total,
                    COALESCE(so.currency_id, company.currency_id) AS currency_id,
                    CASE e.state
                        WHEN 'draft' THEN 'En elaboración'
                        WHEN 'closed' THEN 'Cerrada'
                        WHEN 'signed' THEN 'Firmada'
                        ELSE e.state
                    END AS state_label,
                    'emr.encounter.veterinary'::varchar AS res_model,
                    vet.id AS res_id,
                    e.company_id AS company_id,
                    ('Consulta ' || COALESCE(pet.name, ''))::varchar AS name
                  FROM emr_encounter e
                  JOIN emr_encounter_veterinary vet ON vet.encounter_id = e.id
                  LEFT JOIN sale_order so ON so.id = e.order_id
                  LEFT JOIN res_company company ON company.id = e.company_id
                  LEFT JOIN res_partner pet ON pet.id = e.pet_id
                  LEFT JOIN retail_order retail ON retail.order_id = e.order_id
                UNION ALL
                SELECT
                    -so.id AS id,
                    'venta'::varchar AS move_type,
                    so.date_order AS date,
                    so.pet_id AS pet_id,
                    so.partner_id AS partner_id,
                    COALESCE(so.practitioner_id, seller.partner_id) AS practitioner_id,
                    so.amount_total AS amount_total,
                    so.currency_id AS currency_id,
                    CASE so.state
                        WHEN 'draft' THEN 'Presupuesto'
                        WHEN 'sent' THEN 'Presupuesto enviado'
                        WHEN 'sale' THEN 'Pedido de venta'
                        WHEN 'cancel' THEN 'Cancelado'
                        ELSE so.state
                    END AS state_label,
                    'sale.order'::varchar AS res_model,
                    so.id AS res_id,
                    so.company_id AS company_id,
                    so.name AS name
                  FROM sale_order so
                  JOIN retail_order retail ON retail.order_id = so.id
                  LEFT JOIN res_users seller ON seller.id = so.user_id
            )
            """
            % self._table
        )

    def action_open_origin(self):
        """Abre la consulta o el pedido, que es el documento de origen."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.name or _("Documento"),
            "res_model": self.res_model,
            "res_id": self.res_id,
            "view_mode": "form",
            "views": [[False, "form"]],
            "target": "current",
        }

    @api.model
    def action_new_sale(self):
        """Venta de mostrador: un pedido normal, no un punto de venta."""
        view = self.env.ref("emr_veterinary.sale_order_view_form_counter_sale")
        return {
            "type": "ir.actions.act_window",
            "name": _("Nueva venta"),
            "res_model": "sale.order",
            "view_mode": "form",
            "views": [[view.id, "form"]],
            "target": "current",
            "context": {
                "default_is_appointment": False,
                "emr_veterinary_counter_sale": True,
            },
        }
