import datetime

from odoo import models, fields, _


class WizardFrozenSubscription(models.TransientModel):
    _name = "wizard.frozen.subscription"
    _description = "Wizard Frozen Subscription"

    sale_subscription_id = fields.Many2one(comodel_name="sale.subscription")

    start_frozen_date = fields.Date(string="Start frozen")
    end_frozen_date = fields.Date(string="End frozen")
    reason_frozen = fields.Selection(
        selection=[
            ("free", _("Free")),
            ("paid", _("Paid")),
        ],
        string="Comment"
    )

    def action_create(self):
        self.ensure_one()

        data = {
            "subscription_id": self.sale_subscription_id.id,
            "start_frozen_date": self.start_frozen_date,
            "end_frozen_date": self.end_frozen_date,
            "reason_frozen": self.reason_frozen,
            "stage": "draft",
        }

        if self.start_frozen_date == datetime.date.today():
            data["stage"] = "active"
            self.sale_subscription_id.sudo().write({"stage_id": 4})  # "Frozen"

        self.env["frozen.subscription"].create(data)

        return {"type": "ir.actions.act_window_close"}
