from pytz import timezone

from odoo import models, fields, api, _
from datetime import datetime, timedelta

from odoo.exceptions import UserError


class ClassTraining(models.Model):
    _name = "class.training"
    _description = "Class Training"
    _inherit = "mail.thread"

    def _compute_display_name(self):
        for rec in self:
            # К началу тренировки (по UTC) + время текущего часового пояса пользователя
            difference_time = self._get_timezone_difference_time()

            start_training = False
            if rec.start_training:
                start_training = rec.start_training + timedelta(hours=difference_time)

            rec.display_name = f"{rec.class_group_id.name}, {rec.name}, {start_training}"

    class_group_id = fields.Many2one(
        comodel_name="class.group", string="Class Group", ondelete="cascade")
    name = fields.Char(string="Name")

    state = fields.Selection(
        selection=[
            ("planed", _("Planed")),
            ("completed", _("Completed")),
            ("cancel", _("Cancel")),
        ],
        string="State",
        default="planed",
        index=True
    )
    color = fields.Char(string="Color")
    city = fields.Char(string="City")
    company_id = fields.Many2one(comodel_name="res.company", string="Club")
    location_id = fields.Many2one(comodel_name="class.location", string="Location")
    trainer_id = fields.Many2one(
        comodel_name="hr.employee", string="Trainer", index=True)
    assistant_id = fields.Many2one(
        comodel_name="hr.employee", string="Assistant", index=True)
    class_program_id = fields.Many2one(
        comodel_name="class.program", string="Program", index=True)
    is_trial_training = fields.Boolean(string="Is trial training", index=True)

    date_training = fields.Date(string="Date training")
    time_training = fields.Float(string="Time training")
    start_training = fields.Datetime(
        string="Start training", compute="_compute_start_training", store=True)

    @api.depends("date_training", "time_training")
    def _compute_start_training(self):
        for rec in self:
            start_training = False
            if rec.date_training and rec.time_training:
                hours = int(rec.time_training)
                minutes = int((rec.time_training - hours) * 60)

                difference_time = self._get_timezone_difference_time()

                # Комбинируем дату и время, прибавляя к 00:00 дату начала тренировки +
                # отнимая разницу часового пояса для того что бы фронтенд подставил свою
                # иначе будет на 2 или 3 часа больше
                start_training = datetime.combine(
                    rec.date_training, datetime.min.time()
                ) + timedelta(hours=hours - difference_time, minutes=minutes)

            rec.start_training = start_training

    def _get_timezone_difference_time(self):
        # Получаем часовой пояс пользователя (по умолчанию UTC)
        tz = timezone(self.env.user.tz or "UTC")
        # Получаем разницу времени (+2 или +3 часа)
        return int(
            datetime.now(tz).utcoffset().total_seconds() / 3600)

    duration_training = fields.Float(string="Duration training")
    end_training = fields.Datetime(
        string="End training", compute="_compute_end_training", store=True)

    @api.depends("start_training", "duration_training")
    def _compute_end_training(self):
        for rec in self:
            end_training = False
            if rec.start_training and rec.duration_training:
                hours = int(rec.duration_training)
                minutes = int((rec.duration_training - hours) * 60)

                end_training = rec.start_training + timedelta(
                    hours=hours, minutes=minutes)

            rec.end_training = end_training

    children_ids = fields.One2many(
        comodel_name="class.attendance",
        inverse_name="class_training_id",
        string="Children")

    max_count_children = fields.Integer(string="Max Count Children")
    count_children = fields.Integer(
        string="Number of children", compute="_compute_count_children", store=True)

    @api.depends("children_ids")
    def _compute_count_children(self):
        for rec in self:
            if len(rec.children_ids) > rec.max_count_children:
                raise UserError(_(
                    "Number of children cannot be greater than %(count)s",
                    count=rec.max_count_children
                ))

            rec.count_children = len(rec.children_ids)

    quantity_free_place = fields.Integer(
        string="Quantity free place",
        compute="_compute_quantity_free_place",
        store=True
    )

    @api.depends("max_count_children", "count_children")
    def _compute_quantity_free_place(self):
        for rec in self:
            if rec.max_count_children and rec.count_children:
                rec.quantity_free_place = rec.max_count_children - rec.count_children
            else:
                rec.quantity_free_place = 0

    full_training = fields.Boolean(
        compute="_compute_full_training", string="Full training", store=True)

    @api.depends("max_count_children", "count_children")
    def _compute_full_training(self):
        for rec in self:
            if rec.count_children == rec.max_count_children:
                rec.full_training = True
            else:
                rec.full_training = False

    without_freez = fields.Integer(
        compute="_compute_without_freez",
        string="Number of children without freez",
        store=True
    )

    @api.depends("children_ids.subscription_frozen")
    def _compute_without_freez(self):
        for rec in self:
            if rec.children_ids:
                rec.without_freez = len(rec.children_ids.filtered(
                    lambda x: not x.subscription_frozen))
            else:
                rec.without_freez = 0

    presence = fields.Integer(compute="_compute_presence", string="Presence", store=True)

    @api.depends("children_ids.on_training")
    def _compute_presence(self):
        for rec in self:
            if rec.children_ids:
                rec.presence = len(rec.children_ids.filtered(lambda x: x.on_training))
            else:
                rec.presence = 0

    # def _raise_error_count_children(self, max_count_children):
    #     raise UserError(_(
    #         "Number of children cannot be greater than %(count)s",
    #         count=max_count_children
    #     ))

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:

    #         # Проверка на максимальное кол-во детей на тренировке
    #         if len(vals["children_ids"]) > vals["max_count_children"]:
    #             self._raise_error_count_children(vals["max_count_children"])
    #
    #     return super(ClassTraining, self).create(vals_list)

    # def write(self, vals):
    #     res = super(ClassTraining, self).write(vals)
    #
    #     # Проверка на максимальное кол-во детей на тренировке
    #     if len(self.children_ids) > self.max_count_children:
    #         self._raise_error_count_children(self.max_count_children)
    #
    #     return res

    def completed_training(self):
        self.state = "completed"
        attendances = self.env["class.attendance"].search([
            ("class_training_id", "=", self.id)])
        attendances.write({"state": "completed"})

    def cancel_training(self):
        self.state = "cancel"
        attendances = self.env["class.attendance"].search([
            ("class_training_id", "=", self.id)]).unlink()
        # attendances.write({"state": "cancel"})

    # Метод добавления ученика на пробное занятие (проверка на возможность
    # группы принимать учеников на пробные занятия происходит до вызова метода,
    # вместимость группы не учитывается)
    def add_child_trial_training(self, child_id):  # child_id - res.partner id
        if child_id in self.children_ids.mapped("child_id.id"):
            raise UserError(_("This child already been added in training session!"))

        if self.is_trial_training:
            attendance_id = self.env["class.attendance"].sudo().create({
                "class_training_id": self.id,
                "child_id": child_id,
                "start_training": self.start_training,
                "end_training": self.end_training,
                "company_id": self.company_id.id,
                "color": self.color,
                "duration_training": self.duration_training,

                "trial_training": True,
            }).id
            self.children_ids = [(4, attendance_id)]
        else:
            raise UserError(_("A trial record for this training is prohibited!"))
