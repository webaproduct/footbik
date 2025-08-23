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

    # <--------------------------Добавление на intro-------------------------->
    view_group_add_intro = fields.Boolean(compute="_compute_view_group_add_intro")

    """Проверяем наличие метки qualification=True в добавленных товарах, если хотя в 1 
    есть, отображаем группу для записи на intro"""
    @api.depends("order_line")
    def _compute_view_group_add_intro(self):
        for rec in self:
            view_group_add_intro = False
            if rec.order_line and rec.order_line.mapped(
                    lambda x: x.product_template_id).filtered(lambda y: y.qualification):
                view_group_add_intro = True

            rec.view_group_add_intro = view_group_add_intro


    program_id = fields.Many2one(
        comodel_name="class.program", string="Program", index=True)

    def _get_default_domain(self):
        return [
            ("class_program_id", "=", self.program_id.id),
            ("is_trial_training", "=", True),
            ("state", "=", "planed"),
            ("full_training", "=", False),
            ("company_id", "=", self.company_id.id),
        ]

    domain_training_1_id = fields.Binary(
        compute="_compute_domain_training_1_id", store=False)

    @api.depends("program_id", "training_2_id")
    def _compute_domain_training_1_id(self):
        for rec in self:
            if rec.program_id:
                domain = rec._get_default_domain()

                if rec.training_2_id:
                    domain.append(("id", "!=", rec.training_2_id.id))

                rec.domain_training_1_id = domain
            else:
                rec.domain_training_1_id = [("id", "=", 0)]

    training_1_id = fields.Many2one(
        comodel_name="class.training", string="Training class 1", index=True)

    domain_training_2_id = fields.Binary(
        compute="_compute_domain_training_2_id", store=False)

    @api.depends("program_id", "training_1_id")
    def _compute_domain_training_2_id(self):
        for rec in self:
            if rec.program_id:
                domain = rec._get_default_domain()

                if rec.training_1_id:
                    domain.append(("id", "!=", rec.training_1_id.id))

                rec.domain_training_2_id = domain
            else:
                rec.domain_training_2_id = [("id", "=", 0)]

    training_2_id = fields.Many2one(
        comodel_name="class.training", string="Training class 2", index=True)

    def action_add_child_on_trial_trainings(self):
        self.ensure_one()
        self.training_1_id.add_child_trial_training(self.partner_id.id)
        self.training_2_id.add_child_trial_training(self.partner_id.id)
        self.added_trial_training = True

    added_trial_training = fields.Boolean(string="Added trial training")

    @api.onchange("training_1_id", "training_2_id")
    def _onchange_added_trial_training(self):
        self.ensure_one()
        if not self.training_1_id and not self.training_2_id:
            self.added_trial_training = False

    # <--------------------------Добавление на intro-------------------------->

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
