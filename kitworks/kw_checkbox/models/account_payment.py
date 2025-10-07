import logging

import odoo
from odoo import models, fields, api, exceptions, _
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    kw_checkbox_is_register_receipt = fields.Boolean(
        default=False, string='Register CheckBox receipt')
    kw_checkbox_is_journal_register_receipt = fields.Boolean(
        related='journal_id.kw_checkbox_is_register_receipt')
    kw_checkbox_receipt_id = fields.Many2one(
        comodel_name='kw.checkbox.receipt',
        string='Receipt', )
    kw_checkbox_invoice_id = fields.Many2one(
        comodel_name='account.move', string='Invoice', )
    kw_checkbox_cashier_id = fields.Many2one(
        comodel_name='kw.checkbox.cashier',
        string='Cashier', )
    kw_checkbox_cashier_ids = fields.Many2many(
        comodel_name='kw.checkbox.cashier',
        compute='_compute_kw_checkbox_cashier_ids', )
    kw_checkbox_cash_register_id = fields.Many2one(
        comodel_name='kw.checkbox.cash.register',
        string='Cash register', )
    kw_checkbox_cash_register_ids = fields.Many2many(
        comodel_name='kw.checkbox.cash.register',
        compute='_compute_kw_checkbox_cash_register_ids', )

    @api.depends('journal_id')
    def _compute_kw_checkbox_cashier_ids(self):
        for obj in self:
            ids = self.env.user.kw_checkbox_cashier_ids
            obj.kw_checkbox_cashier_ids = [(6, 0, ids.ids)]

    @api.depends('journal_id')
    def _compute_kw_checkbox_cash_register_ids(self):
        for obj in self:
            ids = self.env['kw.checkbox.cash.register'].search([])
            obj.kw_checkbox_cash_register_ids = [(6, 0, ids.ids)]

    @api.constrains(
        'kw_checkbox_is_register_receipt', 'kw_checkbox_cashier_id',
        'kw_checkbox_cash_register_id', )
    def constrains_checkbox_fields(self):
        for obj in self:
            if obj.kw_checkbox_is_register_receipt and not \
                    obj.journal_id.kw_checkbox_is_register_receipt:
                raise exceptions.ValidationError(
                    _('This journal payment cant be registered as checkbox '
                      'receipt'))

    @api.model
    def default_get(self, field_list):
        rec = super(AccountPayment, self).default_get(field_list)
        invoice_defaults = self.new(
            {'reconciled_invoice_ids': rec.get('reconciled_invoice_ids')}
        ).reconciled_invoice_ids
        if invoice_defaults:
            rec['kw_checkbox_invoice_id'] = invoice_defaults[0].id
        return rec

    def get_payment_goods(self):
        self.ensure_one()
        goods = {"id": self.env["kw.checkbox.receipt"].generate_uuid(),
                 'goods': [], 'discounts': [], 'payments': []}
        payment_method_type = (
            self.journal_id.kw_checkbox_payment_method_type
        )
        payment_method_name = (
            self.journal_id.kw_checkbox_payment_method_name or ' '
        )
        if self.journal_id.type == 'cash':
            goods['payments'].append({
                'code': payment_method_type,
                "type": "CASH",
                "value": round(self.amount * 100),
                "label": payment_method_name,
            })
        else:
            goods['payments'].append({
                'code': payment_method_type,
                "type": "CASHLESS",
                "value": round(self.amount * 100),
                "label": payment_method_name,
            })
        company_id = self.kw_checkbox_invoice_id.company_id
        cash_register_id = self.kw_checkbox_cash_register_id
        for line in self.kw_checkbox_invoice_id.invoice_line_ids.filtered(
                lambda x: not x.price_unit == 0):
            name = line.product_id.name if line.product_id else False
            if line.display_type == 'rounding':
                name = line.product_id.name if line.product_id \
                    else company_id.kw_checkbox_rounding_text
            cb_tax_ids = line.tax_ids.mapped('kw_checkbox_tax_ids').filtered(
                lambda x: (x.cash_register_id.id == cash_register_id.id))
            sum_tax = round(sum([
                tax.compute_all(line.price_unit)['total_included']
                for tax in line.tax_ids]) * 100) or line.price_unit * 100
            if line.price_unit < 0:
                goods['discounts'].append({
                    "type": "DISCOUNT",
                    "mode": "VALUE",
                    "value": 0 - sum_tax,
                    'tax_codes': cb_tax_ids.mapped('code'),
                    'name': name
                })
                continue
            if not line.quantity:
                continue
            if line.quantity < 0:
                goods['discounts'].append({
                    "type": "DISCOUNT",
                    "mode": "VALUE",
                    "value": sum_tax,
                    'tax_codes': cb_tax_ids.mapped('code'),
                    'name': name
                })
                continue
            uktzed = line.product_id.product_tmpl_id.kw_checkbox_uktzed
            uktzed = str(uktzed) if uktzed else ''
            barcode = line.product_id.product_tmpl_id.barcode
            barcode = str(barcode) if (barcode and cash_register_id.
                                       is_pass_barcode_to_checkbox) else ''
            if line.discount:
                product_discount = [{
                    'type': 'DISCOUNT',
                    'mode': 'PERCENT',
                    'value': line.discount,
                }]
            else:
                product_discount = []
            goods['goods'].append({
                'quantity': line.quantity * 1000,
                'is_return': line.move_id.move_type == 'out_refund',
                'discounts': product_discount,
                'good': {
                    'code': line.product_id.id, 'name': name,
                    'excise_barcodes':
                        [x.name for x in line.kw_checkbox_excise_barcode_ids],
                    'tax': cb_tax_ids.mapped('code'),
                    'barcode': barcode,
                    'uktzed': uktzed, 'price': sum_tax, }, })
        return goods

    def action_post(self):
        # _logger.info('post kw_checkbox_is_register_receipt')
        for obj in self:
            if self._context.get('mixed_payment'):
                return super(AccountPayment, self).action_post()
            if not obj.kw_checkbox_is_register_receipt:
                continue
            environment = api.Environment(self.env.cr, odoo.SUPERUSER_ID, {})
            checkbox = obj.kw_checkbox_cashier_id.get_checkbox(
                environment=environment)
            if not checkbox:
                continue
            if float_compare(
                    obj.amount,
                    obj.kw_checkbox_invoice_id.amount_total,
                    precision_rounding=0.01):
                raise exceptions.ValidationError(
                    _('Checkbox: Payment amount can not be different than '
                      'total amount'))
            goods = obj.get_payment_goods()
            receipt = self.env['kw.checkbox.receipt'].sell(
                environment=environment,
                cashier_id=obj.kw_checkbox_cashier_id,
                cash_register_id=obj.kw_checkbox_cash_register_id,
                payload=goods, )
            receipt.invoice_id = obj.kw_checkbox_invoice_id.id
            receipt.payment_id = obj.id
            receipt.wait_receipt_done(
                environment=environment,
                token=obj.kw_checkbox_cashier_id.access_token)
            receipt.update_info(environment=environment)
        return super(AccountPayment, self).action_post()

    def action_reshipping(self):
        for obj in self:
            if not obj.kw_checkbox_is_register_receipt:
                continue
            if obj.kw_checkbox_invoice_id.kw_checkbox_receipt_ids:
                continue
            checkbox = obj.kw_checkbox_cashier_id.get_checkbox()
            if not checkbox:
                continue
            if float_compare(
                    obj.amount,
                    obj.kw_checkbox_invoice_id.amount_total,
                    precision_rounding=0.01):
                raise exceptions.ValidationError(
                    _('Checkbox: Payment amount can not be different than '
                      'total amount'))
            goods = obj.get_payment_goods()
            receipt = self.env['kw.checkbox.receipt'].sell(
                cashier_id=obj.kw_checkbox_cashier_id,
                cash_register_id=obj.kw_checkbox_cash_register_id,
                payload=goods, )
            receipt.invoice_id = obj.kw_checkbox_invoice_id.id
            receipt.payment_id = obj.id
            receipt.wait_receipt_done(obj.kw_checkbox_cashier_id.access_token)
            receipt.update_info()

    def mixed_action_post(self):
        if len(self) < 1:
            return False
        payments = []
        for payment_id in self:
            payment_goods = payment_id.get_payment_goods()
            [payments.append(payment) for payment
             in payment_goods.get('payments', [])]
        obj = self[0]
        if not obj.kw_checkbox_is_register_receipt:
            return False
        environment = api.Environment(self.env.cr, odoo.SUPERUSER_ID, {})
        checkbox = obj.kw_checkbox_cashier_id.get_checkbox(
            environment=environment)
        if not checkbox:
            return False
        goods = obj.get_payment_goods()
        goods['payments'] = payments
        receipt = self.env['kw.checkbox.receipt'].sell(
            environment=environment,
            cashier_id=obj.kw_checkbox_cashier_id,
            cash_register_id=obj.kw_checkbox_cash_register_id,
            payload=goods, )
        receipt.invoice_id = obj.kw_checkbox_invoice_id.id
        receipt.payment_id = obj.id
        receipt.wait_receipt_done(
            environment=environment,
            token=obj.kw_checkbox_cashier_id.access_token)
        receipt.update_info(environment=environment)
        return True
