from odoo import models, api, fields


class AccountPayment(models.Model):
    _inherit = "account.payment"

    account_move_line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="account_payment_id",
        string="Sale data"
    )

    # <--------Поля для вывода в список---------->
    payment_reference_custom = fields.Char(string="Payment reference")
    product_from_account_move_line_id = fields.Many2one(
        comodel_name="product.product", string="Product")
    analytic_from_account_move_line = fields.Json(string="Analytic")
    analytic_precision = fields.Integer()  # Help field for
    # analytic_from_account_move_line and widget="analytic_distribution"

    """Create link between record account.move.line and account.payment if payment have
    rec in reconciled_invoice_ids or kw_checkbox_invoice_id. Filling field 
    ccount_payment_id in account.move.line and we can visible record in one2many field 
    account_move_line_ids
    """
    def _set_link_between_account_move_line_payment(self):
        for rec in self:
            account_move_id = False

            if rec.reconciled_invoice_ids:
                account_move_id = rec.reconciled_invoice_ids[0]  # Invoice account.move
            elif rec.kw_checkbox_invoice_id:
                account_move_id = rec.kw_checkbox_invoice_id  # Invoice account.move

            if account_move_id and account_move_id.invoice_line_ids:
                account_move_line_ids = account_move_id.invoice_line_ids  # Line invoice
                # (product) from account.move

                for line in account_move_line_ids:
                    line.account_payment_id = rec.id

                line = rec.account_move_line_ids[0]  # One2many feild first record
                rec.write({
                    # Add payment reference from account.move
                    "payment_reference_custom": account_move_id.payment_reference,

                    "product_from_account_move_line_id": line.product_id.id,
                    "analytic_from_account_move_line": line.analytic_distribution,
                    "analytic_precision": line.analytic_precision,
                })

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._set_link_between_account_move_line_payment()
        return res
