from odoo import models, api, fields


class AccountPayment(models.Model):
    _inherit = "account.payment"

    payment_reference_custom = fields.Char(
        string="Payment reference", compute="_compute_account_move", store=True)
    product_from_account_move_line_id = fields.Many2one(
        comodel_name="product.product", string="Product",
        compute="_compute_account_move", store=True)
    # analytic_from_account_move_line = fields.Json(
    #     string="Analytic", compute="_compute_account_move", store=True)
    analytic_from_account_move_line = fields.Char(
        string="Analytic", compute="_compute_account_move", store=True)
    # analytic_precision = fields.Integer(
    #     compute="_compute_account_move", store=True)  # Help field for
    # analytic_from_account_move_line and widget="analytic_distribution"

    @api.depends("reconciled_invoice_ids",
                 "kw_checkbox_invoice_id",
                 "kw_checkbox_invoice_id.payment_reference",
                 "kw_checkbox_invoice_id.invoice_line_ids",
                 "kw_checkbox_invoice_id.invoice_line_ids.product_id",
                 "kw_checkbox_invoice_id.invoice_line_ids.analytic_distribution")
    def _compute_account_move(self):
        for rec in self:
            payment_reference_custom = False
            product_from_account_move_line_id = False
            analytic_from_account_move_line = False

            account_move_id = False
            if rec.reconciled_invoice_ids:
                account_move_id = rec.reconciled_invoice_ids[0]  # Invoice account.move
            elif rec.kw_checkbox_invoice_id:
                account_move_id = rec.kw_checkbox_invoice_id  # Invoice account.move

            if account_move_id and account_move_id.invoice_line_ids:
                line = account_move_id.invoice_line_ids[0]

                payment_reference_custom = account_move_id.payment_reference
                product_from_account_move_line_id = line.product_id.id

                if line.analytic_distribution:
                    analytic_id = int(next(iter(line.analytic_distribution)))  # Достаем
                    # первый ключ из словаря {'720': 100.0} -> 720, еще можно вот так
                    # list({'720': 100.0}.keys())[0] -> 720
                    analytic = self.env["account.analytic.account"].browse(
                        analytic_id).name
                    analytic_from_account_move_line = analytic

            rec.payment_reference_custom = payment_reference_custom
            rec.product_from_account_move_line_id = product_from_account_move_line_id
            rec.analytic_from_account_move_line = analytic_from_account_move_line

    status_payment = fields.Char(
        string="Status Payment", compute="_compute_status_payment", store=True)

    @api.depends("state")
    def _compute_status_payment(self):
        for rec in self:
            status_payment = False
            if rec.state:
                status_payment = rec.state

            rec.status_payment = status_payment
