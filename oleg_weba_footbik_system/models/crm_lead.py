import datetime

from odoo import models, fields, api, _
from ..models.res_partner import TYPE_PARENT, GENDER


USER_FOR_WRITE_PAYMENT_TERM_ID = [10]  # 'Системний адміністратор'

MATCHING_NAME_COMPANY_ID = {
    "Форма: Валенсія | Перші кроки – 29.07": 67,  # "Valencia_Centro"
    "Form: Valencia – Free training": 67,  # Valencia_Centro
    "Form: Valencia – Presale": 69,  # Valencia_Raskanya
}

MATCHING_CITY_COMPANY_ID = {
    "Харків": 71,  # Не визначилися з клубом
    "Дніпро": 71,
    "Київ": 71,
    "Ірпінь": 10,  # Ірпінь
    "Запоріжжя": 11,  # Запоріжжя
    "Суми": 12,  # Атріум, м. Суми
    "Одеса": 71,
    "Львів": 71,
    "Луцьк": 18,  # Луцьк
    "Ужгород": 19,  # Ужгород
    "Полтава": 62,  # Полтава
    "Вінниця": 65,  # Вінниця
    "Мукачево": 70,  # Мукачево
    "Бровари": 53,  # ТЦ "Сільпо", м. Бровари
    "Valencia": 71,
}

class CrmLead(models.Model):
    _inherit = "crm.lead"

    """Для передачи payment_term_id по умолчанию в контекст при создании продажи"""
    def action_new_quotation(self):
        res = super().action_new_quotation()
        res["context"]["default_payment_term_id"] = 1
        return res

    @api.depends('partner_id')
    def _compute_name(self):
        for lead in self:
            if not lead.name and lead.partner_id and lead.partner_id.name:
                lead.name = _("%s's client") % lead.partner_id.name

    """При дисквалификации меняем статус на 'Дискваліфіковано' и не архивируем запись"""
    def action_set_lost(self, **additional_values):
        # res = self.action_archive()

        additional_values["stage_id"] = 13  # "Дискваліфіковано"
        if additional_values:
            self.write(dict(additional_values))

        return True

    birthday = fields.Date(string="Birthday", tracking=True)

    @api.onchange("birthday")
    def _onchange_birthday(self):
        self.ensure_one()
        if self.birthday and self.partner_id:
            self.partner_id.birthday = self.birthday

    age = fields.Char(compute="_compute_age", store=False)  # Для обновления на форме
    age_store = fields.Char(string="Age", tracking=True)

    @api.depends("birthday")
    def _compute_age(self):
        for rec in self:
            age = False
            if rec.birthday:
                age = self.env["res.partner"].get_age(rec.birthday)

            rec.age = age
            rec.age_store = age

    skills_id = fields.Many2one(
        comodel_name="skills",
        string="Skills",
    )

    @api.onchange("skills_id")
    def _onchange_skills_id(self):
        self.ensure_one()
        if self.skills_id:
            self.partner_id.skills_id = self.skills_id.id

    need_text = fields.Text(string="Need")
    features_development = fields.Boolean("Features in development")

    gender = fields.Selection(selection=GENDER, string="Gender", tracking=True)

    full_name_parent = fields.Char(string="Full name parent", tracking=True)
    type_parent = fields.Selection(
        selection=TYPE_PARENT, string="Type parent", tracking=True)
    gender_parent = fields.Selection(
        selection=GENDER, string="Gender parent", tracking=True)
    telephone_parent = fields.Char(string="Telephone parent", tracking=True)
    email_parent = fields.Char(string="Email parent", tracking=True)

    domain_parent_id = fields.Binary(compute="_compute_domain_parent_id", store=False)

    @api.depends("partner_id")
    def _compute_domain_parent_id(self):
        for rec in self:
            if rec.partner_id:
                rec.domain_parent_id = [("parent_id", "=", rec.partner_id.id)]
            else:
                rec.domain_parent_id = []

    parent_id = fields.Many2one(
        comodel_name="res.partner", string="Parent", tracking=True)

    telegram = fields.Char(string="Telegram")
    instagram = fields.Char(string="Instagram")
    whatsapp = fields.Char(string="WhatsApp")

    @api.onchange("parent_id")
    def _onchange_full_name_parent(self):
        self.ensure_one()
        if self.parent_id:
            self.write({
                "full_name_parent": self.parent_id.name,
                "type_parent": self.parent_id.type_parent,
                # "gender_parent": self.gender_parent,
                "telephone_parent": self.parent_id.phone,

                "telegram": self.parent_id.phone,
                "instagram": self.parent_id.instagram,
                "whatsapp": self.parent_id.phone,
            })

    # <----------------------------------UTM---------------------------------->
    utm_term_id = fields.Many2one(comodel_name="utm.term", string="utm_term")
    utm_content_id = fields.Many2one(comodel_name="utm.content", string="utm_content")

    medium2_id = fields.Many2one(
        comodel_name="utm.medium", string="Medium", tracking=True)

    domain_source2_id = fields.Binary(compute="_compute_domain_source2_id")

    @api.depends("medium2_id")
    def _compute_domain_source2_id(self):
        for rec in self:
            if rec.medium2_id:
                rec.domain_source2_id = [("medium2_id", "=", rec.medium2_id.id)]
            else:
                rec.domain_source2_id = []

    source2_id = fields.Many2one(
        comodel_name="utm.source", string="Source", tracking=True)

    manager_promouter_id = fields.Many2one(
        comodel_name="hr.employee", string="Manager promouter", tracking=True)
    # <----------------------------------UTM---------------------------------->

    # <--------------------------Добавление на intro-------------------------->
    program_id = fields.Many2one(
        comodel_name="class.program", string="Program", index=True)

    domain_training_id = fields.Binary(
        compute="_compute_domain_training_id", store=False)

    @api.depends("program_id")
    def _compute_domain_training_id(self):
        for rec in self:
            if rec.program_id:
                rec.domain_training_id = [
                    ("class_program_id", "=", rec.program_id.id),
                    ("is_trial_training", "=", True),
                    ("state", "=", "planed"),
                    ("full_training", "=", False),
                    ("company_id", "=", rec.company_id.id),
                    ("start_training", ">=", datetime.datetime.now()),
                ]
            else:
                rec.domain_training_id = [("id", "=", 0)]

    training_id = fields.Many2one(
        comodel_name="class.training", string="Training class", index=True)

    def action_add_child_trial_training(self):
        self.ensure_one()
        self.training_id.add_child_trial_training(self.partner_id.id)
        self.added_trial_training = True

    added_trial_training = fields.Boolean(string="Added trial training")

    @api.onchange("training_id")
    def _onchange_added_trial_training(self):
        self.ensure_one()
        if not self.training_id:
            self.added_trial_training = False

    # <--------------------------Добавление на intro-------------------------->

    # <-----------------Конвертація у нагоду--------------->
    def _handle_partner_assignment(self, force_partner_id=False, create_missing=True):
        for lead in self:
            if force_partner_id:
                lead.partner_id = force_partner_id
            if not lead.partner_id and create_missing:
                child = lead._create_customer()
                lead.partner_id = child.id

                # Custom
                child.write({
                    "company_type": "person",

                    "type_person": "child",
                    "birthday": lead.birthday,
                    "gender": lead.gender,

                    "medium_id": lead.medium_id.id,
                    "source_id": lead.source_id.id,
                    "manager_promouter_id": lead.manager_promouter_id.id,
                })

                # Custom
                parent = self.env["res.partner"].create({
                    "company_type": "person",

                    "type_person": "parent",
                    "name": lead.full_name_parent,
                    "type_parent": lead.type_parent,
                    # "gender": lead.gender_parent,
                    "phone": lead.telephone_parent,
                    "email": lead.email_parent,

                    "parent_id": child.id,
                })

                lead.write({
                    "parent_id": parent.id,

                    "full_name_parent": parent.name,
                    "type_parent": parent.type_parent,
                    # "gender_parent": parent.gender_parent,
                    "telephone_parent": parent.phone,

                    "telegram": parent.phone,
                    "instagram": parent.instagram,
                    "whatsapp": parent.phone,
                })

    # <-----------------Конвертація у нагоду--------------->

    # <------------Кнопка перехода в подписки--------->
    count_subscription = fields.Integer(compute="_compute_count_subscription")

    def _compute_count_subscription(self):
        for rec in self:
            rec.count_subscription = self.env["sale.subscription"].search_count([
                ("partner_id", "=", rec.partner_id.id)
            ])

    def action_open_subscription(self):
        return {
            "name": _("Subscriptions"),
            "type": "ir.actions.act_window",
            "res_model": "sale.subscription",
            "view_mode": "kanban,tree,form",
            "target": "current",
            "domain": [("partner_id", '=', self.partner_id.id)],
            "context": {"default_partner_id": self.partner_id.id}
        }

    # <------------Кнопка перехода в подписки--------->

    # <------------Кнопка перехода в группы--------->
    count_group = fields.Integer(compute="_compute_count_group")

    def _compute_count_group(self):
        for rec in self:
            rec.count_group = self.env["class.group"].search_count([
                ("children_ids", "=", rec.partner_id.id)
            ])

    def action_open_group(self):
        self.ensure_one()
        return {
            "name": _("Groups"),
            "type": "ir.actions.act_window",
            "res_model": "class.group",
            "view_mode": "kanban,tree,form",
            "target": "current",
            "domain": [("children_ids", "=", self.partner_id.id)],
        }

    # <------------Кнопка перехода в группы--------->

    # <------------Кнопка перехода в тренировки--------->
    count_training = fields.Integer(compute="_compute_count_training")

    def _compute_count_training(self):
        for rec in self:
            rec.count_training = self.env["class.training"].search_count([
                ("children_ids.child_id", "=", rec.partner_id.id)
            ])

    def action_open_training(self):
        self.ensure_one()
        return {
            "name": _("Trainings"),
            "type": "ir.actions.act_window",
            "res_model": "class.training",
            "view_mode": "kanban,tree,form",
            "target": "current",
            "domain": [("children_ids.child_id", "=", self.partner_id.id)],
        }

    # <------------Кнопка перехода в тренировки--------->

    # <------------Кнопка перехода в посещения--------->
    count_attendance = fields.Integer(compute="_compute_count_attendance")

    def _compute_count_attendance(self):
        for rec in self:
            rec.count_attendance = self.env["class.attendance"].search_count([
                ("child_id", "=", rec.partner_id.id)
            ])

    def action_open_attendance(self):
        self.ensure_one()
        return {
            "name": _("Attendance"),
            "type": "ir.actions.act_window",
            "res_model": "class.attendance",
            "view_mode": "kanban,tree,form",
            "target": "current",
            "domain": [("child_id", "=", self.partner_id.id)],
        }
    # <------------Кнопка перехода в тренировки--------->

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:

            if vals.get("name"):
                for name, id in MATCHING_NAME_COMPANY_ID.items():
                    if name.lower() in vals["name"].lower():
                        vals["company_id"] = id

            if not vals.get("company_id", False) and vals.get("city"):
                for city, id in MATCHING_CITY_COMPANY_ID.items():
                    if city.lower() in vals["city"].lower():
                        vals["company_id"] = id

        return super().create(vals_list)

    def _cron_calculate_age(self):
        self.env["crm.lead"].search([("birthday", "!=", False)])._compute_age()

    # <-------------------------Для историчных данных------------------------->
    create_date2 = fields.Datetime(string="Create date 2")
    date_convert_to_opportunity = fields.Date(string="Date convert to opportunity")
    need_client = fields.Char(string="Need client")

    def _cron_update_create_date(self):
        records = self.env[self._name].search([
            ("create_date2", "!=", False),
        ]).filtered(lambda x: x.create_date2 != x.create_date)

        for rec in records:
            query = f"UPDATE {self._table} SET create_date=%s WHERE id=%s"
            self.env.cr.execute(query, (rec.create_date2, rec.id))
    # <-------------------------Для историчных данных------------------------->
