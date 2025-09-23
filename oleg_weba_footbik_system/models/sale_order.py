import datetime
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

    """Проверяем наличие метки qualification=True в добавленных товарах, если хотя бы в 1 
    есть, отображаем группу для записи на intro"""
    @api.depends("order_line", "order_line.product_template_id.qualification")
    def _compute_view_group_add_intro(self):
        for rec in self:
            view_group_add_intro = False
            if rec.order_line and rec.order_line.mapped(
                    lambda x: x.product_template_id).filtered(lambda y: y.qualification):
                view_group_add_intro = True

            rec.view_group_add_intro = view_group_add_intro

    status_paid = fields.Boolean(compute="_compute_status_paid")

    @api.depends("invoice_ids")
    def _compute_status_paid(self):
        for rec in self:
            if rec.invoice_ids:
                # Если все инвойсы оплачены - True, иначе - False
                rec.status_paid = all(rec.invoice_ids.mapped(
                    lambda x: True if x.payment_state == "paid" else False))
            else:
                rec.status_paid = False

    program_id = fields.Many2one(
        comodel_name="class.program", string="Program", index=True)

    def _get_default_domain(self):
        return [
            ("class_program_id", "=", self.program_id.id),
            # ("is_trial_training", "=", True),
            ("state", "=", "planed"),
            ("full_training", "=", False),
            ("company_id", "=", self.company_id.id),
            ("start_training", ">=", datetime.datetime.now()),
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

    def action_add_child_on_trial_training_1(self):
        self.ensure_one()
        if self.training_1_id:
            self.training_1_id.add_child_qualification(self.partner_id.id)
            self.added_trial_training_1 = True

    def action_add_child_on_trial_training_2(self):
        self.ensure_one()
        if self.training_2_id:
            self.training_2_id.add_child_qualification(self.partner_id.id)
            self.added_trial_training_2 = True

    added_trial_training_1 = fields.Boolean(string="Added trial training 1")
    added_trial_training_2 = fields.Boolean(string="Added trial training 2")

    @api.onchange("training_1_id", "training_2_id")
    def _onchange_added_trial_training(self):
        self.ensure_one()
        if not self.training_1_id:
            self.added_trial_training_1 = False

        if not self.training_2_id:
            self.added_trial_training_2 = False

    # <-------------------------------------------------------------------->

    is_required_sub_program_id_group_id = fields.Boolean(
        compute="_compute_is_required_sub_program_id_group_id")

    """Проверяем наличие метки subscription=True в добавленных товарах, если хотя бы в 1 
    есть: поля sub_program_id и sub_group_id - обязательны"""
    @api.depends("order_line", "order_line.product_template_id.subscription")
    def _compute_is_required_sub_program_id_group_id(self):
        for rec in self:
            is_required_sub_program_id_group_id = False
            if rec.order_line and rec.order_line.mapped(
                    lambda x: x.product_template_id).filtered(lambda y: y.subscription or
                                                                        y.qualification):
                is_required_sub_program_id_group_id = True

            rec.is_required_sub_program_id_group_id = is_required_sub_program_id_group_id

    sub_program_id = fields.Many2one(
        comodel_name="class.program", string="Program", index=True)

    @api.onchange("sub_program_id")
    def _onchange_sub_program_id(self):
        self.ensure_one()
        if self.sub_program_id:
            self.program_id = self.sub_program_id.id

    domain_sub_group_id_sub = fields.Binary(
        compute="_compute_sub_domain_group_id", store=False)

    @api.depends("sub_program_id")
    def _compute_sub_domain_group_id(self):
        for rec in self:
            if rec.sub_program_id:
                rec.domain_sub_group_id_sub = [
                    ("class_program_id", "=", rec.sub_program_id.id),
                    ("full_group", "=", False),
                    ("company_id", "=", rec.company_id.id),
                ]
            else:
                rec.domain_sub_group_id_sub = [("id", "=", 0)]

    sub_group_id = fields.Many2one(
        comodel_name="class.group", string="Group", index=True)

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
                    "company_id": self.company_id.id,

                    "close_reason_id": False,  # Custom
                    "stage_id": 1,  # Custom
                    "date_start": date_start,  # Custom
                    "recurring_next_date": date_start,  # Custom

                    "program_id": self.sub_program_id.id,  # Custom
                    "group_id": self.sub_group_id.id,  # Custom
                }
            )
            rec.group_id.add_children_in_group_and_trainings(
                rec.partner_id.id, rec.id)  # Добавление ребенка в группу и тренировки у
            # которых дата начала >= дате начала подписки

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
