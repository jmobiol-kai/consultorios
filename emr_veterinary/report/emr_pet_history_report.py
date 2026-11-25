##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class ReportPetHistory(models.AbstractModel):
    """La historia clínica de una mascota, para imprimir.

    Atenciones cerradas o firmadas, de la más nueva a la más vieja, más el
    peso y las vacunas. No incluye obra social: el circuito veterinario no
    la usa.
    """

    _name = "report.emr_veterinary.report_pet_history"
    _description = "Historia clínica de la mascota"

    @api.model
    def _get_report_values(self, docids, data=None):
        pets = self.env["emr.pet"].browse(docids)
        Encuentro = self.env["emr.encounter"]
        historia = {}
        for pet in pets:
            encuentros = Encuentro.search(
                [
                    ("pet_id", "=", pet.id),
                    ("state", "in", ("closed", "signed")),
                ],
                order="date desc, id desc",
            )
            historia[pet.id] = [
                {
                    "encuentro": enc,
                    "detalle": self._detalle(enc),
                    "plantilla": enc.encounter_type_id.report_template,
                }
                for enc in encuentros
            ]
        return {
            "doc_ids": docids,
            "doc_model": "emr.pet",
            "docs": pets,
            "historia": historia,
        }

    def _detalle(self, encuentro):
        if not encuentro.res_model or not encuentro.res_id:
            return self.env["emr.encounter.veterinary"]
        detalle = self.env[encuentro.res_model].browse(encuentro.res_id)
        return detalle if detalle.exists() else self.env["emr.encounter.veterinary"]
