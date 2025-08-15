import logging
import re

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ConversationWizard(models.TransientModel):
    _name = 'kw.conversation.wizard.echat'
    _description = 'Conversation Wizard'

    chat_ids = fields.Many2many(
        required=True,
        comodel_name='kw.chatbot.chat')
    partner_id = fields.Many2one(
        comodel_name='res.partner', required=True, )
    mobile = fields.Char(
        required=True, )

    text = fields.Text()

    @api.model
    def default_get(self, vals):
        res = super(ConversationWizard, self).default_get(vals)
        partner_id = self.env['res.partner'].sudo().browse(
            self.env.context.get('active_id'))
        chat_id = self.env['kw.chatbot.chat'].sudo().search([
            ('provider', '=', 'echat')], limit=1)
        res['chat_ids'] = [(6, 0, chat_id.ids)]
        res['mobile'] = partner_id.mobile or partner_id.phone
        return res

    @api.onchange('mobile')
    def _onchange_mobile_remove_spaces(self):
        if self.mobile:
            self.mobile = self.mobile.replace(' ', '')

    def _check_echat_phone_format(self):
        phone_regex = r'^\+380\d{9}$'
        for record in self:
            if record.mobile and re.match(phone_regex, record.mobile):
                return True
        return False

    def add_conversation(self):
        self.ensure_one()
        self._onchange_mobile_remove_spaces()
        if not self._check_echat_phone_format():
            raise ValidationError(_(
                'The phone number must be in the format '
                '+380 followed by 9 digits in either.'))
        data = {
            'id': "%s | %s" % (self.mobile, self.partner_id.id),
            'name': "%s | %s" % (self.partner_id.name, self.mobile),
            'phone': self.mobile,
            'number': self.mobile,
            'sender': {
                'name': "%s | %s" % (self.partner_id.name, self.mobile),
                'phone': self.mobile,
            },
            'contact': {
                'name': "%s | %s" % (self.partner_id.name, self.mobile),
                'number': self.mobile,
            }
        }
        for chat in self.chat_ids:
            sender_id = self.env['kw.chatbot.sender'].sudo().get_or_create(
                messenger=chat.messenger_id,
                echat_messanger=chat.echat_messanger,
                json_data=data,
                sender=data,
            )

            if not sender_id.partner_id:
                sender_id.write({'partner_id': self.partner_id.id})

            conv_id = self.env['kw.chatbot.conversation'].sudo().get_or_create(
                chat=chat, message=chat.messenger_id, sender=sender_id)
            self.partner_id.mobile = self.mobile
            if self.text:
                try:
                    conv_id.livechat_open_and_subscribe_button()
                    c_id = self.env['kw.chatbot.conversation'].sudo().search([
                        ('user_id', '=', self.env.user.id),
                        ('wired_conversation_id', '=', conv_id.id)], limit=1)
                    c_id.send_message(self.text)
                except Exception as e:
                    sender_id.unlink()
                    _logger.info(e)
                    raise ValidationError(_(
                        'Unable to start a conversation with this partner.'))
