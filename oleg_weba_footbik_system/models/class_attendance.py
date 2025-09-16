from odoo import models, fields


class ClassAttendance(models.Model):
    _inherit = "class.attendance"

    age = fields.Char(related="child_id.age_store", store=True, index=True)
    sum_pay = fields.Float(related="subscription_id.sum_pay", store=True, index=True)
    date_pay = fields.Date(related="subscription_id.date_pay", store=True, index=True)
