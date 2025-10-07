import logging
import time

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from .checkbox import CheckBoxApi

_logger = logging.getLogger(__name__)

OPEN_SHIFT_STATUS = ['CREATED', 'OPENING', 'OPENED', 'CLOSING']


class CheckboxCashier(models.Model):
    _name = 'kw.checkbox.cashier'
    _inherit = ['kw.checkbox.mixin']
    _description = 'Checkbox Cashier'
    _sql_constraints = [
        ('cb_id_uniq', 'unique (cb_id)', _('CheckBox ID must be unique'))]

    name = fields.Char(
        readonly=True, )
    active = fields.Boolean(
        default=True, )
    username = fields.Char(
        required=True, )
    password = fields.Char(
        required=True, )
    access_token = fields.Char(
        readonly=True, )
    cb_id = fields.Char(
        string='CheckBox ID', readonly=True, )
    key_id = fields.Char(
        readonly=True, )
    signature_type = fields.Char(
        readonly=True, )
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', change_default=True,
        default=lambda self: self.env.user.company_id.id, )
    user_ids = fields.Many2many(
        comodel_name='res.users', string='Users',
        relation='kw_checkbox_cashier_res_users_rel',
        column1='cashier_id', column2='user_id', )
    organization_cb_id = fields.Char(
        string='Organization CheckBox ID', readonly=True, )
    organization_id = fields.Many2one(
        comodel_name='kw.checkbox.organization', readonly=True, )
    is_log_enabled = fields.Boolean(
        default=False, )

    @api.model
    def get_cashier_token(self):
        for cashier in self:
            checkbox = cashier.get_checkbox()
            if checkbox:
                return checkbox.access_token
        return False

    def get_checkbox(self, environment=False):
        self.ensure_one()
        checkbox = CheckBoxApi(
            environment=environment,
            access_token=self.access_token,
            test_mode=self.company_id.kw_checkbox_mode != 'prod')
        try:
            checkbox.cashier_me()
        except Exception as e:
            _logger.debug(e)
            checkbox = CheckBoxApi(
                environment=environment,
                username=self.username, password=self.password,
                test_mode=self.company_id.kw_checkbox_mode != 'prod')
            self.write({'access_token': checkbox.cashier_signin()})
            return checkbox
        else:
            return checkbox

    def update_info(self):
        self.ensure_one()
        checkbox = self.get_checkbox()
        res = checkbox.cashier_me()
        self.write({
            'key_id': res['key_id'], 'signature_type': res['signature_type'],
            'cb_id': res['id'], 'name': res['full_name'],
            'organization_cb_id': res['organization']['id'], })
        if not self.organization_id:
            org = self.env['kw.checkbox.organization'].search([
                ('cb_id', '=', res['organization']['id'])], limit=1)
            if not org:
                org = self.env['kw.checkbox.organization'].create({
                    'cb_id': res['organization']['id'], })
            self.organization_id = org.id
        self.organization_id.write({
            'name': res['organization']['title'],
            'edrpou': res['organization']['edrpou'],
            'tax_number': res['organization']['tax_number'], })

    def action_shifts(self):
        self.ensure_one()
        action = self.env.ref(
            'kw_checkbox.kw_checkbox_kw_checkbox_shift_action_window'
            '').read()[0]
        action['domain'] = [('cashier_id', '=', self.id)]
        return action

    def update_shifts(self, environment=False):
        self.ensure_one()
        checkbox = self.get_checkbox(environment=environment)
        res = checkbox.shifts_get({
            'status': ['CREATED', 'OPENING', 'OPENED', 'CLOSING',
                       'CLOSED'],
            'desc': True, 'limit': 25, 'offset': 0, })
        for r in res['results']:
            r['cashier'] = {'id': self.cb_id}
            self.env['kw.checkbox.shift'].get_or_create(r)

    def update_open_shifts(self, environment=False):
        self.ensure_one()
        checkbox = self.get_checkbox(environment=environment)
        res = checkbox.shifts_get({
            'status': ['CREATED', 'OPENING', 'OPENED', 'CLOSING', ],
            'desc': True, 'limit': 25, 'offset': 0, })
        for r in res['results']:
            r['cashier'] = {'id': self.cb_id}
            self.env['kw.checkbox.shift'].get_or_create(r)

    def open_checkbox_shift(self, register_id, environment=False):
        self.ensure_one()
        checkbox = self.get_checkbox(environment=environment)
        self.update_shifts(environment=environment)
        checkbox_shift_ids = self.env['kw.checkbox.shift'].sudo().search([
            ('cashier_id', '=', self.id)])
        if not checkbox_shift_ids.filtered(
                lambda x: x.status in OPEN_SHIFT_STATUS):
            checkbox.license_key = register_id.license_key
            res = checkbox.shift_open()
            if 'message' in res:
                _logger.info(res.get('message'))
            try:
                if res and res.get('status'):
                    self.update_open_shifts(environment=environment)
                    shift = self.env['kw.checkbox.shift'].sudo().search([
                        ('cb_id', '=', res.get('id')),
                        ('name', '=', res.get('serial'))])
                    while shift.status != 'OPENED':
                        time.sleep(1)
                        shift.update_info_by_token(
                            environment=environment,
                            token=checkbox.access_token,)
            except Exception as e:
                _logger.info('Open Checkbox Shift')
                _logger.info('++++++++++++++++++++++++++++++++++++++++++++++')
                _logger.info(e)
                _logger.info('++++++++++++++++++++++++++++++++++++++++++++++')

    def checking_users_other_cashiers(self):
        for obj in self:
            if not obj.user_ids:
                continue
            domain = [
                ('user_ids', 'in', obj.user_ids.ids), ('id', '!=', obj.id)]
            if obj.organization_id:
                domain.append(
                    ('organization_id', '=', obj.organization_id.id))
            if self.search_count(domain):
                raise UserError(_(
                    'One of the users is already listed with other cashiers'))

    def write(self, vals):
        res = super(CheckboxCashier, self).write(vals)
        self.checking_users_other_cashiers()
        return res

    @api.model_create_multi
    def create(self, vals):
        res = super(CheckboxCashier, self).create(vals)
        res.checking_users_other_cashiers()
        return res
