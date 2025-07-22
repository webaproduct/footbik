from odoo import models, fields


class UtmSource(models.Model):
    _inherit = "utm.source"

    medium2_id = fields.Many2one(comodel_name="utm.medium", string="utm_medium")
