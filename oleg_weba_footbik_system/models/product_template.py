from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    subscription = fields.Boolean(string="Subscription")
    qualification = fields.Boolean(string="Qualification")
