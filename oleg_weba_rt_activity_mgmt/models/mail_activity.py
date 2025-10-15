from odoo import models, fields, api


class MailActivity(models.Model):
    _inherit = "mail.activity"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        compute="_compute_company_id",
        compute_sudo=True,
        store=True,
        index=True,
    )

    @api.depends("res_model", "res_id")
    def _compute_company_id(self):
        for rec in self:
            company_id = False
            if rec.res_model and rec.res_id:
                company_id = self.env[rec.res_model].browse(rec.res_id).company_id.id
            rec.company_id = company_id
