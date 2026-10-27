##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class ReportPatientHistory(models.AbstractModel):
    """La historia clínica completa de un paciente, para imprimir.

    Junta todas sus atenciones en un solo documento, de la más nueva a la más
    vieja, y a cada una la dibuja con el cuerpo de su tipo: la misma plantilla
    que usa el informe individual. Nada se escribe dos veces.

    La lógica va acá y no en el QWeb porque decidir qué atenciones entran y en
    qué orden es una regla, no una presentación: lo que se lleva el paciente
    tiene que ser reproducible y auditable.
    """

    _name = "report.emr.report_patient_history"
    _description = "Historia clínica completa"

    @api.model
    def _get_report_values(self, docids, data=None):
        pacientes = self.env["res.partner"].browse(docids)
        no_pacientes = pacientes.filtered(lambda p: not p.is_patient)
        if no_pacientes:
            raise UserError(
                _("%s no es un paciente.", no_pacientes[0].display_name)
            )

        Encuentro = self.env["emr.encounter"]
        historia = {}
        for paciente in pacientes:
            # Sin las descartadas: una atención archivada es un ausente o un
            # error, y no forma parte de la historia del paciente. Y sin las
            # que están en elaboración, que todavía no dicen nada.
            encuentros = Encuentro.search(
                [
                    ("partner_id", "=", paciente.id),
                    ("state", "in", ("closed", "signed")),
                ],
                order="date desc, id desc",
            )
            historia[paciente.id] = [
                {
                    "encuentro": enc,
                    "detalle": self._detalle(enc),
                    "plantilla": enc.encounter_type_id.report_template,
                }
                for enc in encuentros
            ]

        return {
            "doc_ids": docids,
            "doc_model": "res.partner",
            "docs": pacientes,
            "historia": historia,
        }

    def _detalle(self, encuentro):
        """El registro del tipo concreto, que es donde están los campos."""
        if not encuentro.res_model or not encuentro.res_id:
            return None
        detalle = self.env[encuentro.res_model].browse(encuentro.res_id)
        return detalle if detalle.exists() else None
