from odoo import models, fields, _, api


class ClassAttendance(models.Model):
    _name = "class.attendance"
    _description = "Class Attendance"
    _inherit = "mail.thread"

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.class_training_id.name}, {rec.child_id.name}"

    sequence = fields.Integer(string="Sequence", default=1)
    number_sequence = fields.Integer(
        string="№", compute="_compute_number_sequence", store=False)

    def _compute_number_sequence(self):
        for training in self.mapped("class_training_id"):
            childrens = training.children_ids.sorted(lambda x: x.sequence)
            for _id, child in enumerate(childrens, start=1):
                child.number_sequence = _id

    class_training_id = fields.Many2one(
        comodel_name="class.training", string="Training class", ondelete="cascade",
        index=True)

    subscription_id = fields.Many2one(
        comodel_name="sale.subscription", string="Subscription")
    subscription_product = fields.Char(
        string="Product", compute="_compute_subscription_product", store=True)

    @api.depends("subscription_id")
    def _compute_subscription_product(self):
        for rec in self:
            if rec.subscription_id and rec.subscription_id.sale_subscription_line_ids:
                product_id = rec.subscription_id.sale_subscription_line_ids[0]
                rec.subscription_product = product_id.display_name
            else:
                rec.subscription_product = ""

    state = fields.Selection(
        selection=[
            ("planed", _("Planed")),
            ("completed", _("Completed")),
        ],
        string="State",
        default="planed",
        index=True
    )
    child_id = fields.Many2one(
        comodel_name="res.partner",
        string="Child",
        index=True,
        required=True,
        domain=[("is_company", "=", False), ("type_person", "=", "child")]
    )

    phone = fields.Char(string="Phone", related="child_id.phone", store=True, index=True)
    comment = fields.Char(string="Comment")

    # def _phone_get_number_fields(self):  # For sms templates
    #     return ["phone"]

    def _mail_get_partner_fields(self, introspect_fields=False):  # For sms templates
        return ["child_id"]

    start_training = fields.Datetime(string="Start training")
    end_training = fields.Datetime(string="End training")
    duration_training = fields.Float(string="Duration training")

    on_training = fields.Boolean(string="On training", index=True)
    working_off = fields.Boolean(string="Working off", index=True)
    trial_training = fields.Boolean(string="Trial training", index=True)
    subscription_frozen = fields.Boolean(string="Subscription frozen", index=True)
    qualification = fields.Boolean(string="Qualification", index=True)

    color = fields.Char(
        string="Color", related="class_training_id.color", store=True, index=True)
    company_id = fields.Many2one(
        related="class_training_id.company_id", string="Club", store=True, index=True)

    # Метод заморозки абонемента у ученика в тренировках которые еще не закончены
    def freeze_subscription_child(self, child_id):  # child_id - res.partner id
        self.env["class.attendance"].search([
            ("child_id", "=", child_id),
            ("state", "=", "planed"),
        ]).write({"subscription_frozen": True})

    # Метод разморозки абонемента у ученика в тренировках которые еще не закончены
    def unfreeze_subscription_child(self, child_id):  # child_id - res.partner id
        self.env["class.attendance"].search([
            ("child_id", "=", child_id),
            ("state", "=", "planed"),
        ]).write({"subscription_frozen": False})
