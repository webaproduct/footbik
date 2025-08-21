from odoo import models, fields


class ClassTypeNumbering(models.Model):
    _name = "class.type.numbering"
    _description = "Class Type Numbering"

    name = fields.Char(string="Type numbering")
