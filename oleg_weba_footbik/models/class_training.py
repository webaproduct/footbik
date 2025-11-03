import pytz

from odoo import models, fields, api, _
from datetime import datetime, timedelta, time, date

from odoo.exceptions import UserError


class ClassTraining(models.Model):
    _name = "class.training"
    _description = "Class Training"
    _inherit = "mail.thread"
    _order = "start_training asc"

    @api.depends("class_group_id.name", "name", "start_training")
    def _compute_display_name(self):
        tz = pytz.timezone(self.env.user.tz or "UTC")
        for rec in self:
            parts = []
            if rec.class_group_id and rec.class_group_id.name:
                parts.append(rec.class_group_id.name)
            if rec.name:
                parts.append(rec.name)

            if rec.start_training:
                # rec.start_training в Odoo хранится как naive UTC
                local_dt = pytz.UTC.localize(rec.start_training).astimezone(tz)
                # Визуально будет совпадать с введённым стеночным временем (учтён DST на
                # дату)
                # Выберите формат под себя:
                dt_txt = local_dt.strftime('%d.%m.%Y %H:%M:%S')  # напр. 14.10.2025 09:00
                parts.append(dt_txt)

            rec.display_name = ", ".join(parts) if parts else _("New")

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
    color = fields.Char(
        string="Color", related="class_group_id.color", store=True, index=True)
    city = fields.Char(string="City")
    company_id = fields.Many2one(
        related="class_group_id.company_id", string="Club", store=True, index=True)
    location_id = fields.Many2one(comodel_name="class.location", string="Location")
    trainer_id = fields.Many2one(
        related="class_group_id.trainer_id", string="Trainer", store=True, index=True)
    assistant_id = fields.Many2one(
        related="class_group_id.assistant_id",
        string="Assistant",
        store=True,
        index=True
    )
    class_program_id = fields.Many2one(
        string="Program",
        related="class_group_id.class_program_id",
        store=True,
        index=True
    )
    is_trial_training = fields.Boolean(string="Is trial training", index=True)

    date_training = fields.Date(string="Date training")
    time_training = fields.Float(string="Time training")
    start_training = fields.Datetime(
        string="Start training", compute="_compute_start_training", store=True)

    # @api.depends("date_training", "time_training")
    # def _compute_start_training(self):
    #     for rec in self:
    #         start_training = False
    #         if rec.date_training and rec.time_training:
    #             hours = int(rec.time_training)
    #             minutes = int((rec.time_training - hours) * 60)
    #
    #             difference_time = self._get_timezone_difference_time()
    #
    #             # Комбинируем дату и время, прибавляя к 00:00 дату начала тренировки +
    #             # отнимая разницу часового пояса для того что бы фронтенд подставил свою
    #             # иначе будет на 2 или 3 часа больше
    #             start_training = datetime.combine(
    #                 rec.date_training, datetime.min.time()
    #             ) + timedelta(hours=hours - difference_time, minutes=minutes)
    #
    #         rec.start_training = start_training
    #
    def _get_timezone_difference_time(self):
        # Получаем часовой пояс пользователя (по умолчанию UTC)
        tz = pytz.timezone(self.env.user.tz or "UTC")
        # Получаем разницу времени (+2 или +3 часа)
        return int(
            datetime.now(tz).utcoffset().total_seconds() / 3600)

    @api.depends("date_training", "time_training")
    def _compute_start_training(self):
        user_tz_name = self.env.user.tz or "UTC"
        tz = pytz.timezone(user_tz_name)

        for rec in self:
            rec.start_training = False
            if rec.date_training and rec.time_training is not None:
                hours = int(rec.time_training)
                minutes = int(round((rec.time_training - hours) * 60))
                # «Стеночное» локальное время на КОНКРЕТНУЮ дату
                naive_local = datetime.combine(rec.date_training, time(hours, minutes))
                try:
                    local_aware = tz.localize(naive_local, is_dst=None)  # корректно
                    # учтёт DST на эту дату
                except pytz.AmbiguousTimeError:
                    # Осенний откат часов (времени 02:30 существует дважды).
                    # Выбираем зимнее (стандартное) время, чтобы визуально совпадало с
                    # тем, что ввёл пользователь.
                    local_aware = tz.localize(naive_local, is_dst=False)
                except pytz.NonExistentTimeError:
                    # Весенний перевод (напр. 02:30 «не существует»): сдвигаем на час
                    # вперёд.
                    local_aware = tz.localize(
                        naive_local + timedelta(hours=1), is_dst=True)

                # В БД Odoo хранит naive-UTC, поэтому снимаем tzinfo после перевода в UTC
                rec.start_training = local_aware.astimezone(pytz.UTC).replace(
                    tzinfo=None)

    duration_training = fields.Float(
        related="class_group_id.duration_training", string="Duration training")
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
        string="Children"
    )

    children_ids_readonly = fields.Boolean(
        compute="_compute_children_ids_readonly", store=False)

    def _compute_children_ids_readonly(self):
        for rec in self:
            rec.children_ids_readonly = rec.date_training < date.today()

    max_count_children = fields.Integer(
        related="class_group_id.max_count_children", string="Max Count Children")
    count_children = fields.Integer(
        string="Number of children", compute="_compute_count_children", store=True)

    @api.depends("children_ids")
    def _compute_count_children(self):
        for rec in self:
            rec.count_children = len(rec.children_ids)

    @api.constrains("children_ids")
    def _check_max_count_children(self):
        for rec in self:
            if rec.count_children > rec.max_count_children:
                raise UserError(_(
                    "Number of children in training (id - %(id)s, name - %(name)s) "
                    "cannot be greater than: %(count)s",
                    id=rec.id,
                    name=rec.display_name,
                    count=rec.max_count_children
                ))

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
    #
    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #
    #         # Проверка на максимальное кол-во детей на тренировке
    #         if len(vals["children_ids"]) > vals["max_count_children"]:
    #             self._raise_error_count_children(vals["max_count_children"])
    #
    #     return super(ClassTraining, self).create(vals_list)
    #
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
            data = self._get_data_attendance(child_id)

            attendance_id = self.env["class.attendance"].sudo().create(data)
            attendance_id.trial_training = True

            self.children_ids = [(4, attendance_id.id)]
        else:
            raise UserError(_("A trial record for this training is prohibited!"))

    # Метод добавления ученика на квалификацию
    def add_child_qualification(self, child_id):  # child_id - res.partner id
        if child_id in self.children_ids.mapped("child_id.id"):
            raise UserError(_("This child already been added in qualification in "
                              "training session!"))

        data = self._get_data_attendance(child_id)

        attendance_id = self.env["class.attendance"].sudo().create(data)
        attendance_id.qualification = True

        self.children_ids = [(4, attendance_id.id)]

    def _get_data_attendance(self, child_id):
        return {
            "class_training_id": self.id,
            "child_id": child_id,
            "start_training": self.start_training,
            "end_training": self.end_training,
            # "company_id": self.company_id.id,
            # "color": self.color,
            "duration_training": self.duration_training,
        }
