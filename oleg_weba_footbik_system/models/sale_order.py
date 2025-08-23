import logging
from datetime import date

from odoo import models, fields, _, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


USER_FOR_WRITE_PARTNER = [10]  # 'Системний адміністратор'


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_agreement = fields.Boolean(string="Is Agreement")

    date_start_subscription = fields.Date(string="Date start subscription")

    recurring_next_date = fields.Date(string="Next invoice date")

    can_write = fields.Boolean(compute="_compute_can_write")

    @api.depends("partner_id", "payment_term_id")
    def _compute_can_write(self):
        """
        Достаем роли, берем из них всех пользователей, проверяем наличие id текущего
        пользователя в этих ролях, если нет - ошибка
        """
        users = self.env["res.users.role"].sudo().search([
            ("id", "in", USER_FOR_WRITE_PARTNER)
        ]).mapped("line_ids.user_id.id")  # exm. -> [2, 3, 4]

        for rec in self:
            rec.can_write = self.env.uid in users

    def create_subscription(self, lines, subscription_tmpl):
        subscription_lines = []
        for line in lines:
            subscription_lines.append((0, 0, line.get_subscription_line_values()))

        if subscription_tmpl:
            date_start = self.date_start_subscription \
                if self.date_start_subscription \
                else False  # Custom

            rec = self.env["sale.subscription"].create(
                {
                    "partner_id": self.partner_id.id,
                    "user_id": self.env.context.get("uid", self.env.uid),
                    "template_id": subscription_tmpl.id,
                    "pricelist_id": self.partner_id.property_product_pricelist.id,
                    # "date_start": date.today(),  # Custom
                    "sale_order_id": self.id,
                    "sale_subscription_line_ids": subscription_lines,

                    "close_reason_id": False,  # Custom
                    "stage_id": 1,  # Custom
                    "date_start": date_start,  # Custom
                    "recurring_next_date": date_start,  # Custom
                }
            )

            # rec.action_start_subscription()  # Custom. Without start subscription

            self.subscription_ids = [(4, rec.id)]

            if not date_start:  # Custom
                rec.recurring_next_date = self.get_next_interval(
                    subscription_tmpl.recurring_rule_type,
                    subscription_tmpl.recurring_interval,
                )

    def action_confirm(self):
        res = super().action_confirm()

        for rec in self:
            if rec.order_line:  # If there are products
                try:
                    self.env["sale.advance.payment.inv"].with_context({
                        "active_model": "sale.order",
                        "active_ids": [rec.id],
                        "active_id": rec.id,
                        # "default_journal_id": self.company_data['default_journal_sale'].id,
                    }).sudo().create({
                        "advance_payment_method": "delivered",
                    }).sudo().create_invoices()

                    rec.invoice_ids[0].action_post()
                except UserError as e:
                    _logger.error(
                        msg=f"Invoice was not created from sale.order: {rec.id}."
                            f"Error: {e}")

        return res
