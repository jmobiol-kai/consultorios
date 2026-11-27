##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    @api.model
    def _emr_website_label_pay_on_pickup(self):
        """Deja el pago contra entrega como «Pagar al retirar».

        ``delivery`` ya trae ese proveedor manual (sin pasarela). Acá se
        publica, se habilita y se nombra en los idiomas instalados. No se
        vuelve a correr en cada actualización: el dato es noupdate.
        """
        provider = self.env.ref("delivery.payment_provider_cod", raise_if_not_found=False)
        method = self.env.ref(
            "delivery.payment_method_cash_on_delivery", raise_if_not_found=False
        )
        installed = {code for code, _name in self.env["res.lang"].get_installed()}
        langs = [code for code in ("en_US", "es_AR") if code in installed] or ["en_US"]
        message = (
            "<p>El pago se realiza al retirar el pedido en la clínica. "
            "No se cobra online.</p>"
        )
        for lang in langs:
            if provider:
                provider.with_context(lang=lang).write({
                    "name": "Pagar al retirar",
                    "pending_msg": message,
                    "state": "enabled",
                    "is_published": True,
                })
            if method:
                method.with_context(lang=lang).write({
                    "name": "Pagar al retirar",
                    "active": True,
                })
