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

        self.env["frozen.subscription"].create({
            "subscription_id": self.sale_subscription_id.id,
            "start_frozen_date": self.start_frozen_date,
            "end_frozen_date": self.end_frozen_date,
            "reason_frozen": self.reason_frozen,

            "stage": "draft",
        })

        return {"type": "ir.actions.act_window_close"}
