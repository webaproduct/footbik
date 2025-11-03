from odoo import models, fields, api


class ClassAttendance(models.Model):
    _inherit = "class.attendance"

    age = fields.Char(related="child_id.age_store", store=True, index=True)
    sum_pay = fields.Float(related="subscription_id.sum_pay", store=True, index=True)
    date_pay = fields.Date(related="subscription_id.date_pay", store=True, index=True)

    opportunity_id = fields.Many2one(comodel_name="crm.lead", string="Opportunity")

    promoter_id = fields.Many2one(
        comodel_name="res.users",
        related="opportunity_id.user_id",
        string="Promoter",
        store=True,
        tracking=True,
        index=True,
    )
    manager_id = fields.Many2one(
        comodel_name="hr.employee",
        related="opportunity_id.manager_promouter_id",
        string="Manager",
        store=True,
        tracking=True,
        index=True,
    )

    def _search_opportunity(self):
        for rec in self.sudo():
            training_id = rec.class_training_id
            child_id = rec.child_id

            opportunities = self.env["crm.lead"]

            if len(child_id.opportunity_ids) == 1:
                opportunities = child_id.opportunity_ids

            elif rec.trial_training:
                opportunities = child_id.opportunity_ids.filtered(
                    lambda x: x.training_id.id == training_id.id)

            elif rec.qualification:
                sales = child_id.sale_order_ids.filtered(
                    lambda x: x.training_1_id.id == training_id.id
                              or x.training_2_id.id == training_id.id)
                if len(sales) == 1:
                    opportunities = sales.opportunity_id

            elif (rec.subscription_id and rec.subscription_id.sale_order_id and
                  rec.subscription_id.sale_order_id.opportunity_id):
                opportunities = rec.subscription_id.sale_order_id.opportunity_id

            if opportunities and len(opportunities) == 1:
                rec.opportunity_id = opportunities[0].id

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._search_opportunity()
        return res
