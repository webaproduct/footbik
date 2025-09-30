import datetime
import logging

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError

logger = logging.getLogger(__name__)


class SaleSubscription(models.Model):
    _inherit = "sale.subscription"

    is_frozen = fields.Boolean(string="Frozen Subscription")
    frozen_subscription_ids = fields.One2many(
        comodel_name="frozen.subscription",
        inverse_name="subscription_id",
        string="All frozen"
    )

    program_id = fields.Many2one(
        comodel_name="class.program", string="Program", index=True)

    domain_group_id = fields.Binary(compute="_compute_domain_group_id", store=False)

    @api.depends("program_id")
    def _compute_domain_group_id(self):
        for rec in self:
            if rec.program_id:
                rec.domain_group_id = [
                    ("class_program_id", "=", rec.program_id.id),
                    ("full_group", "=", False),
                    ("company_id", "=", rec.company_id.id),
                ]
            else:
                rec.domain_group_id = [("id", "=", 0)]

    group_id = fields.Many2one(comodel_name="class.group", string="Group", index=True)

    date_end = fields.Date(string="End date")
    added_in_group = fields.Boolean()

    sum_pay = fields.Float(string="Sum pay", compute="_compute_sum_pay", store=True)

    @api.depends("amount_total", "invoice_ids.amount_residual",
                 "invoice_ids.state")
    def _compute_sum_pay(self):
        for rec in self:
            _sum = sum(
                rec.invoice_ids.filtered(
                    lambda x: x.move_type == "out_invoice" and
                              x.state != "cancel" and
                              x.payment_state != "paid"
                ).mapped("amount_residual")
            )

            if _sum != 0:
                rec.sum_pay = _sum
            else:
                rec.sum_pay = rec.amount_total

    date_pay = fields.Date(string="Date pay", compute="_compute_date_pay", store=True)

    @api.depends("recurring_next_date", "invoice_ids.amount_residual",
                 "invoice_ids.state", "invoice_ids.invoice_date")
    def _compute_date_pay(self):
        for rec in self:
            recs = rec.invoice_ids.filtered(
                lambda x: x.move_type == "out_invoice" and
                          x.state != "cancel" and
                          x.payment_state != "paid"
            )

            if len(recs) > 1:
                rec.date_pay = recs[-1].invoice_date
            elif len(recs) == 1:
                rec.date_pay = recs.invoice_date
            else:
                rec.date_pay = rec.recurring_next_date

    def write(self, values):
        partner_id = self.partner_id.id

        if values.get("stage_id") and values["stage_id"]:  # Если есть изменения статуса
            # if self.stage_id.id == 1 and values["stage_id"] == 7:
                # "Ready to start" -> "In progress"

                # if self.group_id:
                #     # Добавляем ребенка в группу и незавершенные тренировки
                #     self.group_id.add_children_in_group_and_trainings(partner_id, self.id)

            if values["stage_id"] == 3:  # "Closed"
                if self.group_id:
                    # Удаляем ребенка из группы и незавершенных тренировок
                    self.group_id.delete_children_in_group_and_trainings(partner_id)

                if not self.date_end:
                    values["date_end"] = datetime.date.today()

            if values["stage_id"] == 4:  # "Frozen"
                values["is_frozen"] = True

                if self.group_id:
                    # Делаем пометку заморозки подписки в незавершенных посещениях
                    self.env["class.attendance"].freeze_subscription_child(partner_id)

            if self.stage_id.id == 4:  # "Frozen" -> All other state
                values["is_frozen"] = False

                # Добавляем к дате след. выставления счета кол-во дней заморозки
                if self.recurring_next_date and self.frozen_subscription_ids:
                    frozen_days = self.frozen_subscription_ids[0].frozen_days
                    values["recurring_next_date"] = (
                            self.recurring_next_date +
                            datetime.timedelta(days=frozen_days)
                    )

                # Делаем разморозку подписки в незавершенных посещениях
                self.env["class.attendance"].unfreeze_subscription_child(partner_id)

        if values.get("date") and values["date"]:
            values["date_end"] = values["date"]

        return super(SaleSubscription, self).write(values)

    # <---------------------------Buttons----------------------------->
    """Переопределяем для подсчета кол-во связанных инвойсов без платежей"""
    @api.depends("invoice_ids", "sale_order_ids.invoice_ids")
    def _compute_account_invoice_ids_count(self):
        for record in self:
            record.account_invoice_ids_count = len(self.invoice_ids.filtered(
                lambda x: x.move_type == "out_invoice"
            ))

    """Переопределяем для отображения по кнопке инвойсов без платежей"""
    def action_view_account_invoice_ids(self):
        res = super().action_view_account_invoice_ids()
        res["domain"] = [
            ("id", "in", self.invoice_ids.ids),
            ("move_type", "=", "out_invoice")
        ]
        return res

    def create_frozen_subscription(self):
        self.ensure_one()
        return {
            "name": _("Create Frozen Subscription"),
            "type": "ir.actions.act_window",
            "res_model": "wizard.frozen.subscription",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_sale_subscription_id": self.id,
            },
        }

    def set_action_stage(self):
        self.stage_id = 7  # In progress

    def action_delete_partner_from_group_trainings(self):
        self.group_id.delete_children_in_group_and_trainings(self.partner_id.id)
        self.write({
            "added_in_group": False,
            "group_id": False,
        })

    # <-------------------------------Overwrite----------------------------->
    code = fields.Char(
        string="Reference",
        default=lambda self: self.sudo()
        .env["ir.sequence"]
        .with_company(1)
        .next_by_code("sale.subscription"),  # ТОВ Footbik Україна
    )

    def action_start_subscription(self):
        self.close_reason_id = False
        # in_progress_stage = self.env["sale.subscription.stage"].search(
        #     [("type", "=", "in_progress")], limit=1
        # )
        in_progress_stage = self.env.ref(
            "subscription_oca.subscription_stage_in_progress").id
        self.stage_id = in_progress_stage

    def generate_invoice(self):
        invoice_number = ""
        message_body = ""  # Custom
        msg_static = _("Created invoice with reference")
        if self.template_id.invoicing_mode in ["draft", "invoice", "invoice_send"]:
            invoice = self.create_invoice()
            if self.template_id.invoicing_mode != "draft":
                invoice.action_post()
                mail_template = self.template_id.invoice_mail_template_id
                invoice.with_context(force_send=True)._generate_pdf_and_send_invoice(
                    mail_template
                )
                invoice_number = invoice.name
                message_body = (
                    f"<b>{msg_static}</b> "
                    f"<a href=# data-oe-model=account.move data-oe-id={invoice.id}>"
                    f"{invoice_number}"
                    "</a>"
                )

        if self.template_id.invoicing_mode == "sale_and_invoice":
            order_id = self.create_sale_order()
            order_id.action_confirm()
            order_id.action_lock()
            new_invoice = order_id._create_invoices()
            new_invoice.action_post()
            new_invoice.invoice_origin = order_id.name + ", " + self.name
            invoice_number = new_invoice.name
            message_body = (
                "<b>%s</b> <a href=# data-oe-model=account.move data-oe-id=%d>%s</a>"
                % (msg_static, new_invoice.id, invoice_number)
            )
        if not invoice_number:
            invoice_number = _("To validate")
            message_body = f"<b>{msg_static}</b> {invoice_number}"

        self.calculate_recurring_next_date(self.recurring_next_date)

        if message_body:  # Custom
            self.message_post(body=message_body)

    def create_invoice(self):
        self = self.with_company(self.partner_id.company_id)
        return super(SaleSubscription, self).create_invoice()

    # <-------------------------------CRONS-------------------------------->

    # Крон для поиска ожидающих подписок и активации.
    def _cron_check_subscription_start(self):
        subscriptions = self.env["sale.subscription"].search([
            ("stage_id", "=", 1),  # Ready to start
            ("date_start", "=", datetime.date.today()),
        ])
        if subscriptions:
            for subscription in subscriptions:
                # subscriptions.write({"stage_id": 7})  # In progress
                subscription.action_start_subscription()

                # Нам не нужно создавать инвойс при активации абонемента, т.к. он
                # создается при подтверждении оплаты и связывается с абонементом,
                # остается только пересчитать дату выставления следующего инвойса, если
                # инвойс по какой-то причине не создался из продажи - создаем его.
                try:
                    if not subscription.invoice_ids:
                        subscription.generate_invoice()
                    else:
                        subscription.calculate_recurring_next_date(
                            subscription.recurring_next_date)
                except Exception:
                    logger.exception(
                        f"Error on subscription invoice generate, {subscription.id}")

    # Крон для выборки записей у которых поле "Наступна дата рахунку" == сегодняшней дате
    # и выставление инвойса
    def _cron_check_subscription_generate_invoice(self):
        subscriptions = self.env["sale.subscription"].search([
            ("stage_id", "=", 7),  # In progress
            ("recurring_next_date", "=", datetime.date.today()),
        ])
        if subscriptions:
            for subscription in subscriptions:
                try:
                    subscription.generate_invoice()
                except Exception:
                    logger.exception(
                        f"Error on subscription invoice generate, {subscription.id}")

    # Крон для поиска заканчивающихся подписок и закрытие
    def _cron_check_subscription_end(self):
        subscriptions = self.env["sale.subscription"].search([
            ("stage_id", "=", 7),  # In progress
            ("date_end", "=", datetime.date.today()),
            ("recurring_rule_boundary", "=", False)
        ])
        if subscriptions:
            for subscription in subscriptions:
                subscription.action_close_subscription()
                subscriptions.write({
                    "stage_id": 3,  # Closed
                    "recurring_next_date": False,
                })

    # <-------------------------Для историчных данных------------------------->
    trainer_id = fields.Many2one(comodel_name="hr.employee", string="Trainer")

    create_date2 = fields.Datetime(string="Create date 2")

    def _cron_update_create_date(self):
        records = self.env[self._name].search([
            ("create_date2", "!=", False),
        ]).filtered(lambda x: x.create_date2 != x.create_date)

        for rec in records:
            query = f"UPDATE {self._table} SET create_date=%s WHERE id=%s"
            self.env.cr.execute(query, (rec.create_date2, rec.id))

    date_start2 = fields.Date(string="Date start 2")

    def _cron_update_date_start(self):
        records = self.env[self._name].search([
            ("date_start2", "!=", False),
        ]).filtered(lambda x: x.date_start != x.date_start2)

        for rec in records:
            query = f"UPDATE {self._table} SET date_start=%s WHERE id=%s"
            self.env.cr.execute(query, (rec.date_start2, rec.id))
    # <-------------------------Для историчных данных------------------------->
