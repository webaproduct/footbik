from odoo import models, api


class Lead2OpportunityPartner(models.TransientModel):
    _inherit = "crm.lead2opportunity.partner"

    """Что бы убрать вариант 'nothing' из показа на форме"""
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields=allfields, attributes=attributes)
        if "action" in res and res["action"].get("selection"):
            res["action"]["selection"] = [
                opt for opt in res["action"]["selection"] if opt[0] != "nothing"
            ]
        return res
