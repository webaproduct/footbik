from odoo import models, fields


class UtmTerm(models.Model):
    _name = "utm.term"
    _description = "UTM Term"

    name = fields.Char(string="Name")


class UtmContent(models.Model):
    _name = "utm.content"
    _description = "UTM Content"

    name = fields.Char(string="Name")
