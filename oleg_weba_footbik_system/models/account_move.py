from odoo import models, fields, _
from odoo.exceptions import UserError

USER_FOR_CANCEL_INVOICE = [10, 12]  # 'Системний адміністратор', 'Касир'


class AccountMove(models.Model):
    _inherit = "account.move"

    def button_cancel(self):

        """
        Достаем роли, берем из них всех пользователей, проверяем наличие id текущего
        пользователя в этих ролях, если нет - ошибка
        """
        users = self.env["res.users.role"].sudo().search([
            ("id", "in", USER_FOR_CANCEL_INVOICE)
        ]).mapped("line_ids.user_id.id")  # exm. -> [2, 3, 4]

        if self.env.uid not in users:
            raise UserError(
                _("You can`t cancel Invoice because have`t permission!"))

        return super().button_cancel()

    def action_register_payment(self):
        res = super().action_register_payment()

        kw_checkbox_cashier_id = self.env["kw.checkbox.cashier"].search([
            ("company_id", "=", self.env.company.id)
        ], limit=1)

        kw_checkbox_cash_register_id = self.env["kw.checkbox.cash.register"].search([
            ("cashier_id", "=", kw_checkbox_cashier_id.id)
        ], limit=1)

        res["context"].update({
            "default_kw_checkbox_cashier_id": kw_checkbox_cashier_id.id,
            "default_kw_checkbox_cash_register_id": kw_checkbox_cash_register_id.id,
        })

        return res

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
