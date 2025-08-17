from odoo import models, fields


class ClassAge(models.Model):
    _name = "class.age"
    _description = "Class Age"

    name = fields.Char(string="Age")
