from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    qualification = fields.Boolean(string="Qualification")
