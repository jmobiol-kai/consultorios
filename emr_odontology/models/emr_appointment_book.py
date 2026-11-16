##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models

from .dental_encounter import preferred_encounter_model
from .dental_profile import DENTAL_PROFILE_PARAM, dental_profile_enabled


class EmrAppointmentBook(models.TransientModel):
    _inherit = "emr.appointment.book"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "sale_order_template_id" not in fields_list or not self._emr_dental_profile_on():
            return res
        dental = self.env.ref(
            "emr_odontology.sale_order_template_consulta_odontologica",
            raise_if_not_found=False,
        )
        generic = self.env.ref("emr.sale_order_template_consulta", raise_if_not_found=False)
        current = res.get("sale_order_template_id")
        if dental and (not current or (generic and current == generic.id)):
            res["sale_order_template_id"] = dental.id
        return res

    @api.model
    def _emr_dental_profile_on(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(DENTAL_PROFILE_PARAM, "True")
        )
        return dental_profile_enabled(value)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _emr_dental_profile_on(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(DENTAL_PROFILE_PARAM, "True")
        )
        return dental_profile_enabled(value)

    def _encounter_type(self):
        tipo = super()._encounter_type()
        product_model = tipo.model_name if tipo else ""
        dental = self.env["emr.encounter.type"].search(
            [("model_name", "=", "emr.encounter.odontology")], limit=1
        )
        chosen = preferred_encounter_model(
            product_model,
            self._emr_dental_profile_on(),
            dental_available=bool(dental),
        )
        if dental and chosen == dental.model_name and (
            not tipo or tipo.model_name != dental.model_name
        ):
            return dental
        return tipo

    def _open_encounter(self):
        self._emr_drop_empty_generic_consultation()
        action = super()._open_encounter()
        if action.get("res_model") == "emr.encounter.odontology":
            view = self.env.ref(
                "emr_odontology.emr_encounter_odontology_view_form",
                raise_if_not_found=False,
            )
            if view:
                action["views"] = [[view.id, "form"]]
        return action

    def _emr_encounter_form_view(self):
        view = super()._emr_encounter_form_view()
        if self.encounter_id.res_model == "emr.encounter.odontology":
            dental = self.env.ref(
                "emr_odontology.emr_encounter_odontology_view_form",
                raise_if_not_found=False,
            )
            return dental or view
        return view

    def _emr_drop_empty_generic_consultation(self):
        """Si Atender ahora ya dejó una consulta genérica vacía, no se reabre.

        El perfil odontológico pide el odontograma. La consulta vacía se
        suelta para que la próxima apertura cree la visita dental.
        """
        self.ensure_one()
        encounter = self.encounter_id
        if not encounter or encounter.res_model != "emr.encounter.consultation":
            return
        if not self._emr_dental_profile_on():
            return
        if encounter.state != "draft":
            return
        child = self.env["emr.encounter.consultation"].browse(encounter.res_id)
        if not child.exists():
            self.encounter_id = False
            return
        if (
            (child.reason or "").strip()
            or (child.notes or "").strip()
            or child.lab_line_ids
            or child.diagnosis_ids
        ):
            return
        self.encounter_id = False
        child.unlink()
