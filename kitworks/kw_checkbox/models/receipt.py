import logging

import uuid
import pytz
from odoo import models, fields, api, exceptions, _

from .checkbox import CheckBoxApi

_logger = logging.getLogger(__name__)


class CheckboxReceipts(models.Model):
    _name = 'kw.checkbox.receipt'
    _inherit = ['kw.checkbox.mixin']
    _description = 'Checkbox receipts'
    # _sql_constraints = [
    #     ('cb_id_uniq', 'unique (cb_id)', _('CheckBox ID must be unique'))]

    name = fields.Char(
        string='Fiscal code', readonly=True, )
    active = fields.Boolean(
        default=True, )
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', change_default=True,
        default=lambda self: self.env.user.company_id.id, )
    cb_id = fields.Char(
        string='CheckBox ID', required=True, )
    fiscal_date = fields.Datetime(
        readonly=True, )
    type = fields.Char(
        readonly=True, )
    status = fields.Char(
        readonly=True, )
    cashier_cb_id = fields.Char(
        string='Cashier CheckBox ID', readonly=True, )
    cashier_id = fields.Many2one(
        comodel_name='kw.checkbox.cashier', readonly=True, )
    cash_register_cb_id = fields.Char(
        string='Cash register CheckBox ID', readonly=True, )
    cash_register_id = fields.Many2one(
        comodel_name='kw.checkbox.cash.register', readonly=True, )
    transaction_cb_id = fields.Char(
        string='Transaction CheckBox ID', readonly=True, )
    shift_cb_id = fields.Char(
        string='Shift CheckBox ID', readonly=True, )
    qr_url = fields.Char(
        compute='_compute_url', string='QR-code url', )
    tax_gov_url = fields.Char(
        compute='_compute_url', string='tax.gov.ua url', )
    pdf_url = fields.Char(
        compute='_compute_url', string='PDF url', )
    text = fields.Html(
        readonly=True, )
    res_val = fields.Text(
        string='Response Value', )
    invoice_id = fields.Many2one(
        comodel_name='account.move', )
    payment_id = fields.Many2one(
        comodel_name='account.payment', )

    def get_res_val(self, value):
        return {
            'cashier_name': value.get('cashier_name'),
            'departament': value.get('departament'),
            'goods': value.get('goods'),
            'delivery': value.get('delivery'),
            'discounts': value.get('discounts')
        }

    @api.model
    def get_receipt(self, cashier_id, cash_register_id,
                    params, environment=False):
        # _logger.info(cash_register_id)
        checkbox = cashier_id.get_checkbox(environment=environment)
        checkbox.license_key = cash_register_id.license_key
        res = checkbox.shift()
        res = checkbox.shift_get_receipt(params)
        cashier_id.update_shifts()
        return res

    @api.model
    def generate_uuid(self):
        while True:
            uuid_str = str(uuid.uuid4())
            if not self.search_count([("cb_id", "=", uuid_str)]):
                return uuid_str

    @api.model
    def sell(self, cashier_id, cash_register_id, payload, environment=False):
        # _logger.info(cash_register_id)
        checkbox = cashier_id.get_checkbox(environment=environment)
        checkbox.license_key = cash_register_id.license_key
        res = checkbox.shift()
        res = checkbox.receipts_sell(payload)
        cashier_id.update_shifts(environment=environment)
        return self.create({
            'name': res['fiscal_code'], 'fiscal_date': res['fiscal_date'],
            'status': res['status'], 'cb_id': res['id'], 'type': res['type'],
            'transaction_cb_id': res['transaction']['id'],
            'shift_cb_id': res['shift']['id'], 'cashier_id': cashier_id.id,
            'cash_register_id': cash_register_id.id,
            'cashier_cb_id': cashier_id.cb_id,
            'res_val': self.get_res_val(res),
            'cash_register_cb_id': cash_register_id.cb_id,
            'company_id': cashier_id.company_id.id
        })

    @api.model
    def sell_offline(self, cashier_id, cash_register_id, payload):
        # _logger.info('cash_register_id offline')
        checkbox = cashier_id.get_checkbox()
        checkbox.license_key = cash_register_id.license_key
        res = checkbox.shift()
        res = checkbox.receipts_sell_offline(payload)
        return self.create({
            'name': res['fiscal_code'], 'fiscal_date': res['fiscal_date'],
            'status': res['status'], 'cb_id': res['id'], 'type': res['type'],
            'transaction_cb_id': res['transaction']['id'],
            'shift_cb_id': res['shift']['id'], 'cashier_id': cashier_id.id,
            'cash_register_id': cash_register_id.id,
            'cashier_cb_id': cashier_id.cb_id,
            'res_val': self.get_res_val(res),
            'cash_register_cb_id': cash_register_id.cb_id,
            'company_id': cashier_id.company_id.id
        })

    def update_info_by_token(self, token, environment=False):
        self.ensure_one()
        checkbox = CheckBoxApi(
            environment=environment,
            test_mode=self.company_id.kw_checkbox_mode != 'prod',
            access_token=token, )
        res = checkbox.receipt(self.cb_id)
        data = {'name': res['fiscal_code'], 'fiscal_date': res['fiscal_date'],
                'status': res['status'], 'type': res['type'],
                'transaction_cb_id': res['transaction']['id'],
                'shift_cb_id': res['shift']['id'],
                'cashier_cb_id': res['shift']['cashier']['id'],
                'cash_register_cb_id': res['shift']['cash_register']['id'],
                'text': checkbox.receipt_html(self.cb_id)}
        cashier = self.env['kw.checkbox.cashier'].search([
            ('cb_id', '=', res['shift']['cashier']['id'])], limit=1)
        if cashier:
            data['cashier_id'] = cashier.id
        cash_register = self.env['kw.checkbox.cash.register'].search([
            ('cb_id', '=', res['shift']['cash_register']['id'])], limit=1)
        if cash_register:
            data['cash_register_id'] = cash_register.id
        self.write(data)

    def wait_receipt_done(self, token='', environment=False):  # nosec
        self.ensure_one()
        if not token and self.cashier_id:
            token = self.cashier_id.access_token
        token = self.cashier_id.access_token
        checkbox = CheckBoxApi(
            environment=environment,
            test_mode=self.company_id.kw_checkbox_mode != 'prod',
            access_token=token, )
        return checkbox.wait_receipt_done(self.cb_id)

    def update_info(self, environment=False):
        self.ensure_one()
        cashier_token = None
        if self.cashier_id:
            cashier_token = self.cashier_id.get_checkbox(
                environment=environment).access_token
        elif self.cash_register_id:
            cashier_token = (
                self.cash_register_id.cashier_id.get_cashier_token())
        if not cashier_token:
            raise exceptions.ValidationError(
                _('There is no acceptable username'))
        self.update_info_by_token(cashier_token, environment=environment)

    @api.depends('name', 'fiscal_date', 'cb_id')
    def _compute_url(self):
        checkbox = CheckBoxApi(
            test_mode=self.company_id.kw_checkbox_mode != 'prod', )
        for obj in self:
            obj.qr_url = checkbox.get_url('/receipts/%s/qrcode' % obj.cb_id)
            obj.pdf_url = checkbox.get_url('/receipts/%s/pdf' % obj.cb_id)
            local_tz = pytz.timezone('Europe/Kiev')
            try:
                fiscal_date = fields.Datetime.from_string(obj.fiscal_date)
                fiscal_date = fiscal_date.replace(tzinfo=pytz.utc).astimezone(
                    local_tz)
                obj.tax_gov_url = \
                    'https://cabinet.tax.gov.ua/cashregs/check?id={}&date={}' \
                    ''.format(obj.name, fiscal_date)
            except Exception as e:
                _logger.debug(e)
                obj.tax_gov_url = ''
