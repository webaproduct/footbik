import datetime

from odoo import models, fields, _, api


class FrozenSubscription(models.Model):
    _name = "frozen.subscription"
    _description = "Frozen Subscription"

    def _compute_display_name(self):
        for rec in self:
            stage = dict(
                rec._fields["stage"]._description_selection(self.env)).get(rec.stage)

            rec.display_name = f"{rec.subscription_id.name} - {stage}"

    subscription_id = fields.Many2one(
        comodel_name="sale.subscription", string="Subscription")

    start_frozen_date = fields.Date(string="Start frozen")
    end_frozen_date = fields.Date(string="End frozen")

    reason_frozen = fields.Selection(
        selection=[
            ("free", _("Free")),
            ("paid", _("Paid")),
        ],
        string="Comment"
    )

    frozen_days = fields.Integer(string="Frozen days", compute="_compute_frozen_days")

    @api.depends("start_frozen_date", "end_frozen_date")
    def _compute_frozen_days(self):
        for rec in self:
            if rec.start_frozen_date and rec.end_frozen_date:
                rec.frozen_days = (rec.end_frozen_date - rec.start_frozen_date).days
            else:
                rec.frozen_days = False

    partner_id = fields.Many2one(related="subscription_id.partner_id", store=True)

    stage = fields.Selection(
        string="Stage",
        selection=[
            ("draft", _("Draft")),
            ("active", _("Active")),
            ("done", _("Done")),
            ("cancel", _("Cancel")),
        ],
    )

    def write(self, vals):

        if vals.get("stage"):
            if vals["stage"] == "active":
                self.subscription_id.stage_id = 4  # "Frozen" Переводим подписку на этап
                # 'В заморозці'

            if vals["stage"] in ["done", "cancel"]:
                self.subscription_id.stage_id = 2  # "In progress"  Переводим подписку
                # на этап 'Активний'

        return super().write(vals)

    def action_cancel_frozen_subscription(self):
        self.ensure_one()
        self.stage = "cancel"

    def _cron_start_end_frozen_subscription(self):
        """Переводим запись frozen.subscription и подписку в статус заморожено"""
        self.env["frozen.subscription"].search([
            ("stage", "=", "draft"),
            ("start_frozen_date", "=", datetime.date.today()),
        ]).write({"stage": "active"})

        """Переводим запись frozen.subscription и подписку в статус активно"""
        self.env["frozen.subscription"].search([
            ("stage", "=", "active"),
            ("end_frozen_date", "=", datetime.date.today()),
        ]).write({"stage": "done"})
