##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import hmac

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request


class VeterinaryTurnos(http.Controller):

    @http.route("/turnos", type="http", auth="public", website=True, sitemap=True)
    def turnos(self, practitioner_id=None, **kwargs):
        values = request.env["emr.veterinary.website.booking"].sudo().form_values(
            practitioner_id=practitioner_id
        )
        return request.render("emr_veterinary_website.turnos_page", values)

    @http.route(
        "/turnos/confirmar",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=True,
        sitemap=False,
    )
    def confirmar(self, **post):
        booking = request.env["emr.veterinary.website.booking"].sudo()
        try:
            order = booking.book(post, ip=request.httprequest.remote_addr)
        except (UserError, ValidationError) as err:
            values = booking.form_values(
                practitioner_id=post.get("practitioner_id"),
                post=post,
            )
            values["error"] = str(err.args[0] if err.args else err)
            return request.render("emr_veterinary_website.turnos_page", values)
        if not order:
            return request.render(
                "emr_veterinary_website.turnos_thanks", {"order": False}
            )
        token = order._portal_ensure_token()
        return request.redirect(
            "/turnos/confirmado/%s?access_token=%s" % (order.id, token)
        )

    @http.route(
        "/turnos/confirmado/<int:order_id>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def confirmado(self, order_id, access_token=None, **kwargs):
        order = request.env["sale.order"].sudo().browse(order_id).exists()
        token = order.access_token or "" if order else ""
        if (
            not order
            or not order.pet_id
            or not access_token
            or len(access_token) != len(token)
            or not hmac.compare_digest(token, access_token)
        ):
            raise request.not_found()
        return request.render("emr_veterinary_website.turnos_thanks", {"order": order})
