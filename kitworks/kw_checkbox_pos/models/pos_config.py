import logging

from odoo import models, fields, exceptions, api, _

_logger = logging.getLogger(__name__)


class CheckboxPosConfig(models.Model):
    _inherit = 'pos.config'

    kw_checkbox_cash_register_ids = fields.Many2many(
        comodel_name='kw.checkbox.cash.register',
        compute="_compute_cash_register",
        string='Cash register', )
    kw_checkbox_organization_ids = fields.Many2many(
        comodel_name='kw.checkbox.organization',
        compute="_compute_organization",
        string='Organization', )
    kw_checkbox_category_ids = fields.One2many(
        comodel_name='kw.checkbox.category', inverse_name='pos_config_id',)
    kw_is_checkbox_rounding = fields.Boolean(
        help="This flag enables the checkbox rounding "
             "in the POS, which is certified by law.", default=False)
    kw_is_checkbox_check_in_pos = fields.Boolean(
        help="This flag enables the function of "
             "printing checkbox check in the pos.", default=True)

    def _default_payment_methods(self):
        pass

    @api.onchange('kw_checkbox_category_ids')
    def _compute_cash_register(self):
        self.ensure_one()
        if len(self.kw_checkbox_category_ids) > 1:
            raise exceptions.ValidationError(_(
                'You should add only one checkbox organization'))
        if self.kw_checkbox_category_ids:
            for checkbox_category in self.kw_checkbox_category_ids:
                self.kw_checkbox_cash_register_ids += \
                    checkbox_category.kw_checkbox_cash_register_id
        else:
            self.kw_checkbox_cash_register_ids = False

    @api.onchange('kw_checkbox_category_ids')
    def _compute_organization(self):
        self.ensure_one()
        if self.kw_checkbox_category_ids:
            for checkbox_category in self.kw_checkbox_category_ids:
                self.kw_checkbox_organization_ids += \
                    checkbox_category.kw_checkbox_organization_id
        else:
            self.kw_checkbox_organization_ids = False

    @api.onchange('cash_rounding', 'kw_checkbox_category_ids')
    def onchange_cash_rounding(self):
        for obj in self:
            if obj.kw_checkbox_category_ids:
                obj.only_round_cash_method = True

    @api.onchange('payment_method_ids', 'kw_checkbox_category_ids')
    def payment_method_compare(self):
        self.ensure_one()
        if len(self.kw_checkbox_cash_register_ids.ids) \
                != len(self.kw_checkbox_organization_ids.ids):
            raise exceptions.ValidationError(_('You should add only one cash '
                                               'register by one organization'))
        product_category_ids = self.kw_checkbox_category_ids.mapped(
            'kw_checkbox_product_category_id')
        payment_method_ids = self.payment_method_ids.filtered(
            lambda r: r.kw_checkbox_product_category_id.id
            not in product_category_ids.ids and
            r.kw_checkbox_is_register_receipt)
        if payment_method_ids:
            raise exceptions.ValidationError(_(
                "Please add payment method's "
                "kw_checkbox_product_category_id to POS Config before"
                " use it"))

    @api.constrains('payment_method_ids')
    def payment_method_cash_only_one(self):
        for obj in self:
            payment_method_cash_ids = obj.payment_method_ids.filtered(
                lambda r: r.journal_id.type == 'cash')
            if len(payment_method_cash_ids) >= 2:
                raise exceptions.ValidationError(
                    _("You can add only one type of payment cash"))

    def check_and_sell_offline_orders(self, cash_register_id):
        _logger.info('check_and_sell_offline_order')
        self.ensure_one()
        orders = self.env['pos.order'].search([
            ('is_offline', '=', True),
            ('kw_checkbox_organization_id', '=',
             cash_register_id.organization_id.id)])
        for order in orders:
            order.checkbox_sell_offline()

    def _check_cashier_before_open_session(self):
        self.ensure_one()
        for register in self.kw_checkbox_cash_register_ids:
            register.update_info()
            cashier = self.env['kw.checkbox.cashier'].search(
                [('user_ids', 'in', self.env.user.ids),
                 ('organization_id', '=', register.organization_id.id)],
                limit=1)
            if not cashier:
                raise exceptions.ValidationError(_(
                    'There is no valid cashier for cash register'))

    def open_ui(self):
        self.ensure_one()
        self._check_cashier_before_open_session()
        return super(CheckboxPosConfig, self).open_ui()
