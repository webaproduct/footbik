import random
from datetime import datetime, timedelta

from odoo import models, fields, _, api
from odoo.exceptions import UserError

# 1-1, 1-2, ..., 1-6, 1-А, ..., 12-1, ..., 12-6, 12-А == 84 шт.
COUNT_MAIN_STAGE = 12
COUNT_SUB_STAGE = 7
COUNT_TRAINING = COUNT_MAIN_STAGE * COUNT_SUB_STAGE


class ClassGroup(models.Model):
    _name = "class.group"
    _inherit = "mail.thread"
    _description = "Class Group"

    name = fields.Char(string="Name")

    start_date_for_create_training = fields.Date(
        string="Start date for create training", default=datetime.today(),
        help=_("Date who use for start create training"))
    date_end_training = fields.Date(string="End date for training group")

    photo_group = fields.Binary(string="Photo Group")

    # @staticmethod
    # def generate_random_color():
    #     r = random.randint(0, 255)
    #     g = random.randint(0, 255)
    #     b = random.randint(0, 255)
    #     # Преобразуем в шестнадцатеричный формат и возвращаем в формате #RRGGBB
    #     return f"#{r:02X}{g:02X}{b:02X}"

    # color = fields.Char(string="Color", default=generate_random_color())

    class_program_id = fields.Many2one(
        comodel_name="class.program", string="Program", index=True)
    class_age_id = fields.Many2one(comodel_name="class.age", string="Age", index=True)
    class_color_group_id = fields.Many2one(
        comodel_name="class.color.group", string="Color Group", index=True)

    @api.onchange("class_program_id", "class_age_id")
    def _onchange_color_group_id(self):
        self.ensure_one()
        if self.class_program_id and self.class_age_id:
            class_color_group_id = self.env["class.color.group"].search([
                ("class_program_id", "=", self.class_program_id.id),
                ("class_age_id", "=", self.class_age_id.id),
            ], limit=1)
            if class_color_group_id:
                self.class_color_group_id = class_color_group_id.id
            else:
                self.class_color_group_id = False

    color = fields.Char(related="class_color_group_id.color", store=True)

    type_numbering_id = fields.Many2one(
        comodel_name="class.type.numbering", string="Type numbering")
    trainer_id = fields.Many2one(
        comodel_name="hr.employee", string="Trainer", index=True)
    assistant_id = fields.Many2one(
        comodel_name="hr.employee", string="Assistant", index=True)
    city = fields.Char(string="City")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Club",
        default=lambda self: self.env.company,
        index=True
    )
    location_id = fields.Many2one(comodel_name="class.location", string="Location")
    is_trial_training_group = fields.Boolean(
        string="Is trial training group", default=True, index=True)
    duration_training = fields.Float(string="Duration training", default=0.75)
    information_about_group = fields.Text(string="Information about group")

    training_on_monday = fields.Boolean(string="Monday")
    start_training_monday = fields.Float()

    training_on_tuesday = fields.Boolean(string="Tuesday")
    start_training_tuesday = fields.Float()

    training_on_wednesday = fields.Boolean(string="Wednesday")
    start_training_wednesday = fields.Float()

    training_on_thursday = fields.Boolean(string="Thursday")
    start_training_thursday = fields.Float()

    training_on_friday = fields.Boolean(string="Friday")
    start_training_friday = fields.Float()

    training_on_saturday = fields.Boolean(string="Saturday")
    start_training_saturday = fields.Float()

    training_on_sunday = fields.Boolean(string="Sunday")
    start_training_sunday = fields.Float()

    children_ids = fields.Many2many(
        string="Children",
        comodel_name="res.partner",
        relation="class_group_res_partner_rel",
        column1="class_group_id",
        column2="res_partner_id",
        domain=[("is_company", "=", False), ("type_person", "=", "child")],
    )

    max_count_children = fields.Integer(string="Max Count Children", default=30)
    count_children = fields.Integer(
        string="Number of children", compute="_compute_count_children", store=True)

    @api.depends("children_ids")
    def _compute_count_children(self):
        for rec in self:
            rec.count_children = len(rec.children_ids)

    @api.constrains("children_ids")
    def _check_max_children(self):
        for rec in self:
            if rec.count_children > rec.max_count_children:
                raise UserError(_(
                    "Number of children in group (id - %(id)s, name - %(name)s) "
                    "cannot be greater than: %(count)s",
                    id=rec.id,
                    name=rec.display_name,
                    count=rec.max_count_children
                ))

    full_group = fields.Boolean(
        compute="_compute_full_training", string="Full group", store=True)

    @api.depends("max_count_children", "count_children")
    def _compute_full_training(self):
        for rec in self:
            if rec.count_children == rec.max_count_children:
                rec.full_group = True
            else:
                rec.full_group = False

    training_ids = fields.One2many(
        comodel_name="class.training",
        inverse_name="class_group_id",
        string="Trainings")

    # <---------------Функционал по генерации тренировок и посещений-------------->
    def create_training(self):
        self.ensure_one()
        selected_days = self._get_selected_days()  # Получаем выбранные дни и часы

        weekday_mapping = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        # Сортируем дни недели по порядку
        sorted_days = sorted(selected_days.keys(), key=lambda day: weekday_mapping[day])

        # Определяем начальную дату
        current_date = self.start_date_for_create_training

        # Генерируем тренировки
        trainings = []
        trainings_count = 0
        generate_name = self._generate_name()  # Создаем генератор
        while trainings_count < COUNT_TRAINING:
            for day in sorted_days:
                # Находим ближайший указанный день недели
                # delta_days = ((среда - 2) - (пятница - 4) + 7) % 7 =
                # (2 - 4 + 7) % 7 = 5 % 7 = 5 - кол-во дней до искомого дня недели
                delta_days = (weekday_mapping[day] - current_date.weekday() + 7) % 7
                training_date = current_date + timedelta(days=delta_days)

                # Добавляем занятие, если еще не набрано 84
                if trainings_count < COUNT_TRAINING:
                    # Получаем дефолтные значения для тренировок
                    default_data = self._get_default_data_training()

                    # Расширяем словарь динамическими значениями
                    dynamic_data = {
                        "name": next(generate_name),  # Получаем следующее значение
                        # имени из генератора

                        "date_training": training_date,  # День тренировки
                        "time_training": selected_days[day],  # Время тренировки под
                        # день недели
                    }
                    # Объединяем словари и аккумулируем данные
                    trainings.append(default_data | dynamic_data)
                    trainings_count += 1

                # Переход на следующую неделю
                current_date = training_date + timedelta(days=1)

        # Указываем дату с какой можно будет начать следующее создание тренировок
        self.start_date_for_create_training = current_date + timedelta(days=1)

        # Фиксируем Дату последней тренировки в этой группе
        self.date_end_training = current_date - timedelta(days=1)

        # Создаем записи в базе данных
        created_trainings = self.env["class.training"].create(trainings)

        # Создаем записи посещений
        self._create_attendance(created_trainings, self.children_ids.ids)

    def _get_selected_days(self):
        days = {
            "monday": self.start_training_monday if self.training_on_monday else False,
            "tuesday": self.start_training_tuesday
            if self.training_on_tuesday
            else False,
            "wednesday": self.start_training_wednesday
            if self.training_on_wednesday
            else False,
            "thursday": self.start_training_thursday
            if self.training_on_thursday
            else False,
            "friday": self.start_training_friday if self.training_on_friday else False,
            "saturday": self.start_training_saturday
            if self.training_on_saturday
            else False,
            "sunday": self.start_training_sunday if self.training_on_sunday else False,
        }
        # Фильтруем только выбранные дни
        selected_days = {day: time for day, time in days.items() if time is not False}
        # print(selected_days)  # {'monday': 16.0, 'wednesday': 16.0, 'saturday': 10.5}

        if not selected_days:
            raise UserError(_("No days selected for training generation!"))

        return selected_days

    # Генератор для создания имени тренировки в формате:
    # 1-1, 1-2, ..., 1-6, 1-А, ..., 12-1, ..., 12-6, 12-А == 84 шт.
    @staticmethod
    def _generate_name():
        for i in range(1, COUNT_MAIN_STAGE + 1):  # 12
            for j in range(1, COUNT_SUB_STAGE + 1):  # 7
                if j == COUNT_SUB_STAGE:  # 7
                    yield f"{i} - A"
                else:
                    yield f"{i} - {j}"

    def _get_default_data_training(self):
        return {
            "class_group_id": self.id,
            "city": self.city,
            # "company_id": self.company_id.id,
            "location_id": self.location_id.id,
            # "trainer_id": self.trainer_id.id,
            # "class_program_id": self.class_program_id.id,
            "duration_training": self.duration_training,
            # "color": self.color,
            "max_count_children": self.max_count_children,
            "is_trial_training": self.is_trial_training_group,
            # "assistant_id": self.assistant_id.id,
        }

    def _create_attendance(
            self, trainings: list, children_ids: list[int], subscription_id=None) -> None:
        for training in trainings:
            for child_id in children_ids:
                self.env["class.attendance"].sudo().create({
                    "class_training_id": training.id,

                    "subscription_id": subscription_id if subscription_id else False,

                    "child_id": child_id,
                    "start_training": training.start_training,
                    "end_training": training.end_training,
                    # "company_id": training.company_id.id,
                    # "color": training.color,
                    "duration_training": training.duration_training,
                })

    # <---------------Функционал по генерации тренировок и посещений-------------->

    # Метод добавления ученика в группу и во все тренировки которые еще не закончены
    # (Проверка на вместимость группы происходит до вызова метода)

    """Для добавления ребенка в группу и тренировки (начало тренировки => дате начала 
        подписки) при создании подписки"""
    # child_id - res.partner id, sub_id - sale.subscription id
    def add_children_in_group_and_trainings(self, child_id, sub_id=None):
        self.children_ids = [(4, child_id)]  # Добавляем ученика в группу

        if sub_id:
            sub_id = self.env["sale.subscription"].browse(sub_id)
            trainings = self.training_ids.filtered(
                lambda x: x.state == "planed" and
                          x.start_training.date() >= sub_id.date_start)

            sub_id.added_in_group = True  # Пометка в подписке - ребенок добавлен
            # в группу
        else:
            trainings = self.training_ids.filtered(lambda x: x.state == "planed")

        self._create_attendance(trainings, [child_id], sub_id.id)

    # Метод удаления ученика из группы и всех тренировок которые еще не закончены
    # children_id - res.partner id
    def delete_children_in_group_and_trainings(self, children_id):
        self.children_ids = [(3, children_id)]  # Удаляем ученика из группы

        self.env["class.attendance"].search([
            ("child_id", "=", children_id),
            ("state", "=", "planed"),
            ("start_training", ">=", datetime.now()),
        ]).unlink()
