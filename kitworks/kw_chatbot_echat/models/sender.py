import logging

from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


class Sender(models.Model):
    _inherit = 'kw.chatbot.sender'

    echat_sender_id = fields.Char()

    echat_username = fields.Char()

    echat_mobile_phone = fields.Char()

    @api.model
    def get_or_create(self, messenger,
                      echat_messanger=False, json_data=False, **kwargs):
        if messenger.provider != 'echat':
            return super().get_or_create(messenger, **kwargs)

        json_data = json_data or {}
        sender = False
        sender_id = False
        sender_phone = False
        sender_name = f"Unknown_{json_data.get('number', 'unknown')}"

        if echat_messanger in ('viber', 'whatsapp'):
            contact = json_data.get('contact', {})
            sender_phone = str(contact.get('number', ''))
            sender = self.sudo().search(
                [('echat_mobile_phone', '=', sender_phone)], limit=1)
            if not sender:
                sender = self.get_sender_by_phone(phone=sender_phone)
            sender_name = (json_data.get('contact', {}).get('name', '').strip()
                           or f"Unknown_{json_data.get('number', 'unknown')}")

        elif echat_messanger == 'telegram':
            sender_info = kwargs.get('sender', {})
            sender_id = sender_info.get('id')
            sender_phone = str(sender_info.get('phone', ''))
            sender = self.sudo().search(
                [('echat_mobile_phone', '=', sender_phone)], limit=1)
            if not sender:
                sender = self.get_sender_by_phone(phone=sender_phone)
            sender_name = (kwargs.get('sender', {}).get('name', '').strip()
                           or kwargs.get('sender', {}).get('username', '')
                           or f"Unknown_{kwargs.get('sender', {}).get('id')}")

        if not sender:
            sender = self.sudo().create({
                'name': sender_name,
                'echat_sender_id': sender_id,
                'echat_username': sender_name,
                'echat_mobile_phone': sender_phone,
                'messenger_id': messenger.id, })
        return sender

    def get_sender_by_phone(self, phone):
        try:
            cleaned = ''.join(ch for ch in str(phone or '') if ch.isdigit())
            if cleaned:
                cleaned = f"+{cleaned}"
            sender = self.sudo().search(
                [('echat_mobile_phone', '=', cleaned)],
                limit=1
            )
            return sender
        except Exception as e:
            _logger.exception(f"Error in get_sender_by_phone "
                              f"with phone={phone}: {e}")
            return False

    def aprove_sender(self):
        for obj in self:
            if obj.provider == 'echat':
                raise exceptions.UserError(_(
                    'This sender (E-Chat) cannot become an operator'))
        return super().aprove_sender()

    def reject_sender(self):
        for obj in self:
            if obj.provider == 'echat':
                raise exceptions.UserError(_(
                    'This sender (E-Chat) cannot become an operator'))
        return super().aprove_sender()
