from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    account_payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Payment",
        help="For link between account.move.line and account.payment"
    )
