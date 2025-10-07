import base64
import logging

from datetime import datetime
from typing import List
import requests
from odoo import models, fields, api, exceptions, _
from odoo.tools import float_round

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    kw_checkbox_organization_id = fields.Many2one(
        comodel_name='kw.checkbox.organization', )
    kw_checkbox_receipt_id = fields.Many2one(
        comodel_name='kw.checkbox.receipt', string='Receipt', )
    checkbox_check = fields.Char(
        related='kw_checkbox_receipt_id.name', )
    checkbox_qr = fields.Binary(
        compute='_compute_checkbox_qr', )
    is_offline = fields.Boolean(
        default=False)

    def _compute_checkbox_qr(self):
        for obj in self:
            if obj.kw_checkbox_receipt_id:
                obj.checkbox_qr = base64.b64encode(
                    requests.get(
                        obj.kw_checkbox_receipt_id.qr_url, timeout=30).content)
            else:
                obj.checkbox_qr = False

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        receipt = self.env['kw.checkbox.receipt'].browse(
            ui_order.get('kw_checkbox_receipt_id'))
        if receipt:
            res.update({'checkbox_check_ids': [receipt.id],
                        'checkbox_check': receipt.name,
                        'checkbox_qr': receipt.qr_url, })
        return res

    # pylint: disable=too-many-locals
    def get_order_goods(self):
        self.ensure_one()
        session_id = self.session_id
        cash_register_id = session_id.kw_checkbox_shift_ids.cash_register_id
        goods = {"id": self.env["kw.checkbox.receipt"].generate_uuid(),
                 'goods': [], 'discounts': [], 'payments': [],
                 'context': {'order_id': self.id}}
        cash_payment = self.payment_ids.filtered(
            lambda x: x.payment_method_id.is_cash_count)
        bank_payment = self.payment_ids.filtered(
            lambda x: not x.payment_method_id.is_cash_count)
        if session_id.config_id.cash_rounding:
            goods['rounding'] = True
        if cash_payment:
            cash_payment_method_type = int(fields.first(
                cash_payment
            ).payment_method_id.kw_checkbox_payment_method_type)
            cash_payment_method_name = fields.first(
                cash_payment
            ).payment_method_id.kw_checkbox_payment_method_name or ' '
            goods['payments'].append({
                'code': cash_payment_method_type,
                "type": "CASH",
                "value": round(sum([x.amount for x in cash_payment])*100, 0),
                "label": cash_payment_method_name,
            })
        if bank_payment:
            bank_payment_method_type = int(fields.first(
                bank_payment
            ).payment_method_id.kw_checkbox_payment_method_type)
            back_payment_method_name = fields.first(
                bank_payment
            ).payment_method_id.kw_checkbox_payment_method_name or ' '
            goods['payments'].append({
                'code': bank_payment_method_type,
                "type": "CASHLESS",
                "value": round(sum([x.amount for x in bank_payment])*100, 0),
                "label": back_payment_method_name,
            })
        for line in self.lines.filtered(lambda x: not x.price_unit == 0):
            variant_ids = line.product_id.product_template_attribute_value_ids
            variant = variant_ids.sudo()._get_combination_name()
            # name = ('%s (%s)' % (line.product_id.name, variant)
            #         if variant else line.product_id.name)
            cb_tax_ids = line.product_id.taxes_id.mapped(
                'kw_checkbox_tax_ids').filtered(lambda x: (
                    x.cash_register_id.id == cash_register_id.id))
            sum_tax = round(sum([
                tax.compute_all(line.price_unit)['total_included']
                for tax in line.tax_ids]) * 100 or line.price_unit * 100)
            if line.price_unit < 0:
                goods['discounts'].append({
                    "type": "DISCOUNT",
                    "mode": "VALUE",
                    "value": 0 - sum_tax,
                    'tax_codes': cb_tax_ids.mapped('symbol'),
                    'name': ('%s (%s)' % (line.product_id.name, variant)
                             if variant else line.product_id.name)
                })
                continue
            if not line.qty:
                continue
            if (line.qty < 0 and
                    not line.mapped('refunded_orderline_id.order_id')):
                goods['discounts'].append({
                    "type": "DISCOUNT",
                    "mode": "VALUE",
                    "value": round(
                        ((line.price_subtotal_incl / line.qty) * 100), 2),
                    'tax_codes': cb_tax_ids.mapped('symbol'),
                    'name': ('%s (%s)' % (line.product_id.name, variant)
                             if variant else line.product_id.name)
                })
                continue
            uktzed = '{}'.format(
                line.product_id.product_tmpl_id.kw_checkbox_uktzed) if \
                line.product_id.product_tmpl_id.kw_checkbox_uktzed else ''
            barcode = '{}'.format(line.product_id.product_tmpl_id.barcode) if (
                line.product_id.product_tmpl_id.barcode and
                cash_register_id.is_pass_barcode_to_checkbox) else ''
            excises_chr = []
            for pack in line.pack_excise_ids:
                excises_chr.append(pack.name)
            goods['goods'].append({
                'quantity': line.qty * 1000, 'good': {
                    'code': line.product_id.id,
                    'line_id': line.id,
                    'excise_barcodes': (
                        excises_chr if
                        line.product_id.is_excise_product else []),
                    'name': ('%s (%s)' % (line.product_id.name, variant)
                             if variant else line.product_id.name),
                    'tax': cb_tax_ids.mapped('symbol'),
                    'uktzed': uktzed,
                    'barcode': barcode,
                    'price': round(
                        ((line.price_subtotal_incl / line.qty) * 100), 2)}
            })
        return goods

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    def _kw_create_checkbox_receipt_from_ui(self, res: List[dict]) -> None:
        for order_id in res:
            order = self.browse(order_id['id'])
            ps = self.env["pos.payment"].search(
                [('pos_order_id', '=', order.id)], limit=1)
            j = False
            if not ps or not ps.payment_method_id or \
                    not ps.payment_method_id.kw_checkbox_is_register_receipt:
                continue
            category = ps.payment_method_id.kw_checkbox_product_category_id
            for checkbox_category in order.config_id.kw_checkbox_category_ids:
                if checkbox_category.kw_checkbox_product_category_id \
                        == category:
                    j = checkbox_category
                    break
            if not j:
                continue
            if not order.kw_checkbox_organization_compare(
                    j.kw_checkbox_organization_id):
                raise exceptions.ValidationError(_(
                    'You cant register payment throw this method'))
            if not order.kw_checkbox_organization_id:
                order.kw_checkbox_organization_id = \
                    j.kw_checkbox_organization_id.id
            goods = order.get_order_goods()
            if order.refunded_orders_count > 0:
                goods = order.get_checkbox_refund_goods(goods)
            shift = order.session_id.kw_checkbox_get_shift(
                j.kw_checkbox_organization_id)
            if not shift:
                continue
            if ps.amount < 0 and order.amount_paid < 0:
                # refund
                res_val = goods
                if res_val:
                    cashier_id = shift.cashier_id
                    cash_register_id = shift.cash_register_id
                    checkbox = cashier_id.get_checkbox()
                    checkbox.license_key = cash_register_id.license_key
                    for obj in res_val.get('goods'):
                        obj['is_return'] = True
                    checkbox.shift()
                    payment_method_type = int(
                        ps.payment_method_id.kw_checkbox_payment_method_type
                    )
                    payment_method_name = (
                        ps.payment_method_id.kw_checkbox_payment_method_name
                        or ' '
                    )
                    if ps.payment_method_id.is_cash_count:
                        res_val['payments'] = [
                            {
                                'code': payment_method_type,
                                "type": "CASH",
                                "value": round(ps.amount * 100, 2) * -1,
                                "label": payment_method_name,
                            }
                        ]
                    else:
                        res_val['payments'] = [
                            {
                                'code': payment_method_type,
                                "type": "CASHLESS",
                                "value": round(ps.amount * 100, 2) * -1,
                                "label": payment_method_name,
                            }
                        ]
                    kw_checkbox_receipt_id = self.env[
                        'kw.checkbox.receipt'
                    ].sell(
                        payload=res_val,
                        cashier_id=shift.cashier_id,
                        cash_register_id=shift.cash_register_id,
                    )
                    kw_checkbox_receipt_id.wait_receipt_done()
                    kw_checkbox_receipt_id.update_info()
                    order.kw_checkbox_receipt_id = kw_checkbox_receipt_id.id
                    continue
            if shift and not shift.cash_register_id.is_offline:
                receipt = self.env['kw.checkbox.receipt'].sell(
                    payload=goods,
                    cashier_id=shift.cashier_id,
                    cash_register_id=shift.cash_register_id,
                )
                receipt.wait_receipt_done()
                receipt.update_info()
                order.kw_checkbox_receipt_id = receipt.id
            else:
                order.is_offline = True

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    @api.model
    def create_from_ui(self, orders, draft=False):
        res = super(PosOrder, self).create_from_ui(orders)
        self._kw_create_checkbox_receipt_from_ui(res)
        return res

    def get_checkbox_refund_goods(self, goods):
        self.ensure_one()
        for obj in goods.get('goods'):
            obj['quantity'] = -obj['quantity']
            obj['is_return'] = True
        for payment in goods['payments']:
            if payment.get('value'):
                payment.update({'value': -int(payment.get('value'))})
        return goods

    def kw_checkbox_organization_compare(self, organization_id):
        self.ensure_one()
        if not self.lines:
            return True
        if not self.kw_checkbox_organization_id:
            return True
        if not organization_id:
            return True
        if organization_id.id == self.kw_checkbox_organization_id.id:
            return True
        return False

    def checkbox_refund(self, m_payment_obj):
        self.ensure_one()
        if not self.session_id.config_id.kw_checkbox_category_ids:
            return
        res_val = self.get_order_goods()
        if res_val:
            config_id = m_payment_obj.config_id
            cashier_id = self.kw_checkbox_receipt_id.cashier_id
            cash_register_id = self.kw_checkbox_receipt_id.cash_register_id
            checkbox = cashier_id.get_checkbox()
            checkbox.license_key = cash_register_id.license_key
            # d = literal_eval(res_val)
            for obj in res_val.get('goods'):
                obj['quantity'] = -obj['quantity']
                obj['is_return'] = True
            for payment in res_val.get('payments'):
                if payment.get('type') == 'CASH':
                    if (config_id.cash_rounding and
                            config_id.kw_is_checkbox_rounding):
                        amount = float_round(
                            payment.get('value'),
                            precision_rounding=10.0,
                            rounding_method=(
                                config_id.rounding_method.rounding_method))
                        payment['value'] = amount
                payment['value'] = payment.get('value') * -1
            res2 = checkbox.receipts_sell(res_val)
            kw_checkbox_receipt_id = self.env['kw.checkbox.receipt'].create({
                'status': res2['status'],
                'cb_id': res2['id'],
                'type': res2['type'],
                'transaction_cb_id': res2['transaction']['id'],
                'shift_cb_id': res2['shift']['id'],
                'cashier_id': cashier_id.id,
                'cash_register_id': cash_register_id.id,
                'cashier_cb_id': cashier_id.cb_id,
                'res_val': res2,
                'cash_register_cb_id': cash_register_id.cb_id
            })
            kw_checkbox_receipt_id.wait_receipt_done()
            kw_checkbox_receipt_id.update_info()

            self.kw_checkbox_receipt_id = kw_checkbox_receipt_id.id

    def checkbox_sell_offline(self):
        _logger.info('checkbox_sell_offline')
        self.ensure_one()
        if self.kw_checkbox_organization_id:
            shift = self.get_shift_in_order()
            if not shift or not shift.cash_register_id.is_offline:
                return False
            goods = self.get_order_goods()
            if self.refunded_orders_count > 0:
                goods = self.get_checkbox_refund_goods(goods)
            offline_code = self.env['kw.checkbox.offline.code'].search([
                ('cash_register_id', '=', shift.cash_register_id.id)], limit=1)
            if offline_code:
                current_datetime = datetime.now()
                goods['fiscal_code'] = offline_code.fiscal_code
                goods['fiscal_date'] = \
                    current_datetime.strftime("%Y-%m-%d %H:%M:%S")
                receipt = self.env['kw.checkbox.receipt'].sell_offline(
                    payload=goods, cashier_id=shift.cashier_id,
                    cash_register_id=shift.cash_register_id, )
                receipt.wait_receipt_done()
                receipt.update_info()
                self.kw_checkbox_receipt_id = receipt.id
                offline_code.sudo().active = False
                return True
        return False

    def checkbox_check_and_sell_offline(self):
        self.ensure_one()
        if self.kw_checkbox_organization_id:
            cash_register_id = self.env['kw.checkbox.cash.register'].search([
                ('organization_id', '=',
                 self.kw_checkbox_organization_id.id)], limit=1)
            if not cash_register_id.ping_tax_service():
                raise exceptions.ValidationError(_(
                    "You should use offline mode, because CheckBox"
                    " signature turned off"))
            self.checkbox_sell_offline()

    def create(self, vals_list):
        result = super(PosOrder, self).create(vals_list)
        for obj in result:
            if obj.account_move and obj.kw_checkbox_receipt_id:
                obj.kw_checkbox_receipt_id.sudo().write(
                    {'invoice_id': obj.account_move.id})
        return result

    def write(self, vals):
        res = super(PosOrder, self).write(vals)
        for obj in self:
            if vals.get('kw_checkbox_receipt_id') and obj.account_move:
                obj.kw_checkbox_receipt_id.sudo().write(
                    {'invoice_id': obj.account_move.id})
            if vals.get('account_move') and obj.kw_checkbox_receipt_id:
                obj.kw_checkbox_receipt_id.sudo().write(
                    {'invoice_id': obj.account_move.id})
        return res

    # pylint: disable=R1702,R0912
    def action_reshipping(self):
        for order_id in self:
            order = self.browse(order_id['id'])
            if not order.kw_checkbox_receipt_id:
                ps = self.env["pos.payment"].search(
                    [('pos_order_id', '=', order.id)], limit=1)
                j = False
                if not ps or not ps.payment_method_id or not \
                        ps.payment_method_id.kw_checkbox_is_register_receipt:
                    continue
                category = ps.payment_method_id.kw_checkbox_product_category_id
                for checkbox_category in \
                        order.config_id.kw_checkbox_category_ids:
                    if checkbox_category.kw_checkbox_product_category_id \
                            == category:
                        j = checkbox_category
                        break
                if not j:
                    continue
                if not order.kw_checkbox_organization_compare(
                        j.kw_checkbox_organization_id):
                    raise exceptions.ValidationError(_(
                        'You cant register payment throw this method'))
                if not order.kw_checkbox_organization_id:
                    order.kw_checkbox_organization_id = \
                        j.kw_checkbox_organization_id.id
                goods = order.get_order_goods()
                if order.amount_total < 0:
                    if goods.get('payments'):
                        del goods['payments']
                    for obj in goods.get('goods'):
                        obj['quantity'] = -obj['quantity']
                        obj['is_return'] = True
                        for payment in order.payment_ids:
                            payment_method_type = int(
                                payment
                                .payment_method_id
                                .kw_checkbox_payment_method_type
                            )
                            payment_method_name = (
                                payment
                                .payment_method_id
                                .kw_checkbox_payment_method_name
                                or ' '
                            )
                            if payment.payment_method_id.is_cash_count:
                                goods['payments'] = [
                                    {
                                        'code': payment_method_type,
                                        "type": "CASH",
                                        "value": round(
                                            payment.amount * 100, 2) * -1,
                                        "label": payment_method_name,
                                    }]
                            else:
                                goods['payments'] = [
                                    {
                                        'code': payment_method_type,
                                        "type": "CASHLESS",
                                        "value": round(
                                            payment.amount * 100, 2) * -1,
                                        "label": payment_method_name,
                                    }]
                shift = order.session_id.kw_checkbox_get_shift(
                    j.kw_checkbox_organization_id)
                if shift:
                    receipt = self.env['kw.checkbox.receipt'].sell(
                        payload=goods, cashier_id=shift.cashier_id,
                        cash_register_id=shift.cash_register_id, )
                    receipt.wait_receipt_done()
                    receipt.update_info()
                    order.kw_checkbox_receipt_id = receipt.id
                else:
                    order.is_offline = True

    def get_shift_in_order(self):
        for order_id in self:
            order = self.browse(order_id['id'])
            if not order.kw_checkbox_receipt_id:
                ps = self.env["pos.payment"].search(
                    [('pos_order_id', '=', order.id)], limit=1)
                j = False
                if not ps or not ps.payment_method_id or not \
                        ps.payment_method_id.kw_checkbox_is_register_receipt:
                    continue
                category = ps.payment_method_id.kw_checkbox_product_category_id
                for checkbox_category in \
                        order.config_id.kw_checkbox_category_ids:
                    if checkbox_category.kw_checkbox_product_category_id \
                            == category:
                        j = checkbox_category
                        break
                if not j:
                    continue
                shift = order.session_id.kw_checkbox_get_shift(
                    j.kw_checkbox_organization_id)
                if shift:
                    return shift
        return False
