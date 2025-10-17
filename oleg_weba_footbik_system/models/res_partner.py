import datetime

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta

GENDER = [
    ("male", "Male"),
    ("female", "Female"),
]

TYPE_PARENT = [
    ("mother", "Mother"),
    ("father", "Father"),
    ("brother", "Brother"),
    ("sister", "Sister"),
    ("grandmother", "Grandmother"),
    ("grandfather", "Grandfather"),
    ("nanny", "Nanny"),
    ("guardian", "Guardian")
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    birthday = fields.Date(string="Birthday", tracking=True)
    age = fields.Char(compute="_compute_age", store=False)
    age_store = fields.Char(string="Age", tracking=True)

    @api.depends("birthday")
    def _compute_age(self):
        for rec in self:
            age = False
            if rec.birthday:
                age = rec.get_age(rec.birthday)

            rec.age = age
            rec.age_store = age

    @staticmethod
    def get_age(birthday):
        today = datetime.date.today()
        diff = relativedelta(today, birthday)  # relativedelta(years=+27, months=+5, days=+15)
        return f"{diff.years},{diff.months}" if birthday else ""

    gender = fields.Selection(selection=GENDER, string="Gender", tracking=True)
    type_parent = fields.Selection(
        selection=TYPE_PARENT, string="Type parent", tracking=True)

    medium_id = fields.Many2one(
        comodel_name="utm.medium", ondelete="set null", string="Channel")
    source_id = fields.Many2one(
        comodel_name="utm.source", ondelete="set null", string="Source")

    domain_source_id = fields.Binary(compute="_compute_domain_source_id")

    @api.depends("medium_id")
    def _compute_domain_source_id(self):
        for rec in self:
            if rec.medium_id:
                rec.domain_source_id = [("medium_id", "=", rec.medium_id.id)]
            else:
                rec.domain_source_id = []

    manager_promouter_id = fields.Many2one(
        comodel_name="hr.employee", string="Manager promouter", tracking=True)

    class_program_id = fields.Many2one(
        comodel_name="class.program", string="Program", index=True)
    skills_id = fields.Many2one(comodel_name="skills", string="Skills", tracking=True)
    instagram = fields.Char(string="Instagram", tracking=True)
    telegram = fields.Char(string="Telegram", tracking=True)

    # <------------Кнопка перехода в подписки--------->
    count_subscription = fields.Integer(compute="_compute_count_subscription")

    def _compute_count_subscription(self):
        for rec in self:
            rec.count_subscription = self.env["sale.subscription"].search_count([
                ("partner_id", "=", rec.id)
            ])

    def action_open_subscription(self):
        return {
            "name": _("Subscriptions"),
            "type": "ir.actions.act_window",
            "res_model": "sale.subscription",
            "view_mode": "kanban,tree,form",
            "target": "current",
            "domain": [("partner_id", '=', self.id)],
            "context": {"default_partner_id": self.id, "create": False}
        }
    # <------------Кнопка перехода в подписки--------->

    # <------------Кнопка перехода в группы--------->
    count_group = fields.Integer(compute="_compute_count_group")

    def _compute_count_group(self):
        for rec in self:
            rec.count_group = self.env["class.group"].search_count([
                ("children_ids", "=", rec.id)
            ])

    def action_open_group(self):
        self.ensure_one()
        return {
            "name": _("Groups"),
            "type": "ir.actions.act_window",
            "res_model": "class.group",
            "view_mode": "kanban,tree,form",
            "target": "current",
            "domain": [("children_ids", "=", self.id)],
        }
    # <------------Кнопка перехода в группы--------->

    # <------------Кнопка перехода в тренировки--------->
    count_training = fields.Integer(compute="_compute_count_training")

    def _compute_count_training(self):
        for rec in self:
            rec.count_training = self.env["class.training"].search_count([
                ("children_ids.child_id", "=", rec.id)
            ])

    def action_open_training(self):
        self.ensure_one()
        return {
            "name": _("Trainings"),
            "type": "ir.actions.act_window",
            "res_model": "class.training",
            "view_mode": "kanban,tree,form",
            "target": "current",
            "domain": [("children_ids.child_id", "=", self.id)],
        }
    # <------------Кнопка перехода в тренировки--------->

    # <------------Кнопка перехода в посещения--------->
    count_attendance = fields.Integer(compute="_compute_count_attendance")

    def _compute_count_attendance(self):
        for rec in self:
            rec.count_attendance = self.env["class.attendance"].search_count([
                ("child_id", "=", rec.id)
            ])

    def action_open_attendance(self):
        self.ensure_one()
        return {
            "name": _("Attendance"),
            "type": "ir.actions.act_window",
            "res_model": "class.attendance",
            "view_mode": "kanban,tree,form",
            "target": "current",
            "domain": [("child_id", "=", self.id)],
        }
    # <------------Кнопка перехода в тренировки--------->

    def _cron_calculate_age(self):
        self.env["res.partner"].search([("birthday", "!=", False)])._compute_age()

    # <-------------------------Для историчных данных------------------------->
    create_date2 = fields.Datetime(string="Create date 2")

    def _cron_update_create_date(self):
        records = self.env[self._name].search([
            ("create_date2", "!=", False),
        ]).filtered(lambda x: x.create_date2 != x.create_date)

        for rec in records:
            query = f"UPDATE {self._table} SET create_date=%s WHERE id=%s"
            self.env.cr.execute(query, (rec.create_date2, rec.id))
    # <-------------------------Для историчных данных------------------------->
