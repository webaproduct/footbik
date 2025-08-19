import datetime

from odoo import models, fields, api, _


class SaleSubscription(models.Model):
    _inherit = "sale.subscription"

    is_frozen = fields.Boolean(string="Frozen Subscription")
    frozen_subscription_ids = fields.One2many(
        comodel_name="frozen.subscription",
        inverse_name="subscription_id",
        string="All frozen"
    )

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

    group_id = fields.Many2one(
        comodel_name="class.group", string="Group", ondelete="cascade", index=True)

    date_end = fields.Date(string="End date")
    close_reason_id = fields.Many2one()

    def write(self, values):
        partner_id = self.partner_id.id

        if values.get("stage_id") and values["stage_id"]:  # Если есть изменения статуса
            if self.group_id:  # Если указана группа
                if self.stage_id.id == 1 and values["stage_id"] == 2:
                    # "Ready to start" -> "In progress"

                    # Добавляем ребенка в группу и незавершенные тренировки
                    self.group_id.add_children_in_group_and_trainings(partner_id, self.id)

                if values["stage_id"] == 3:  # "Closed"
                    # Удаляем ребенка из группы и незавершенных тренировок
                    self.group_id.delete_children_in_group_and_trainings(partner_id)

                if values["stage_id"] == 4:  # "Frozen"
                    values["is_frozen"] = True

                    # Делаем пометку заморозки подписки в незавершенных посещениях
                    self.env["class.attendance"].freeze_subscription_child(partner_id)

                if self.stage_id.id == 4:  # "Frozen" -> All other state
                    values["is_frozen"] = False

                    # Добавляем к дате след. выставления счета кол-во дней заморозки
                    if self.recurring_next_date:
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

    # Крон для поиска ожидающих подписок и активации
    def _cron_check_subscription_start(self):
        subscriptions = self.env["sale.subscription"].search([
            ("stage_id", "=", 1),  # Ready to start
            ("date_start", "=", datetime.date.today()),
        ])
        if subscriptions:
            subscriptions.write({"stage_id": 2})  # In progress

    # Крон для поиска заканчивающихся подписок и закрытие
    def _cron_check_subscription_end(self):
        subscriptions = self.env["sale.subscription"].search([
            ("stage_id", "=", 2),  # In progress
            ("date_end", "=", datetime.date.today()),
        ])
        if subscriptions:
            subscriptions.write({"stage_id": 3})  # Closed
