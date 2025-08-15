import logging
import base64
import uuid

import requests
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class Conversation(models.Model):
    _inherit = 'kw.chatbot.conversation'

    is_echat_send = fields.Boolean()

    def get_or_create_partner(self, sender_id, company_id=False):
        if self.chat_id.messenger_id.provider != 'echat':
            return super().get_or_create_partner(sender_id, company_id)
        partner_id = sender_id.partner_id
        if not sender_id.partner_id:
            partner_id = self.env['res.partner'].sudo().create({
                'name': sender_id.name, })
            if company_id:
                partner_id.write({'company_id': company_id.id, })
            sender_id.write({'partner_id': partner_id.id})

        tag = self.env['res.partner.category'].search([
            ('name', '=', self.chat_id.name), ])
        if not tag:
            tag = self.env['res.partner.category'].create({
                'name': self.chat_id.name,
                'partner_ids': partner_id.ids})
        tag.write({'partner_ids': [(4, partner_id.id)]})
        if self.sender_id.echat_sender_id:
            parent_tag_id = self.env['res.partner.category'].search([
                ('name', '=', 'E-Chat'), ])
            if not parent_tag_id:
                self.env['res.partner.category'].create({
                    'name': 'E-Chat',
                    'partner_ids': partner_id.ids, })
            parent_tag_id.write({'partner_ids': [(4, partner_id.id)]})
            return partner_id
        return None

    @api.model
    def get_or_create(self, chat, **kwargs):
        if chat.messenger_id.provider != 'echat':
            return super().get_or_create(chat, **kwargs)
        sender = kwargs.get('sender')
        if not sender:
            raise ValueError('Cant process: "sender_id" not provided')
        conversation = self.sudo().search([
            ('sender_id', '=', sender.id),
            ('company_id', '=', chat.company_id.id),
            ('chat_id', '=', chat.id)], limit=1)
        if not conversation:
            conversation = self.sudo().create({
                'name': sender.echat_username,
                'dialog_id': chat.dialog_id.id,
                'company_id': chat.company_id.id,
                'sender_id': sender.id,
                'chat_id': chat.id, })
            if conversation.dialog_id.is_partner:
                self.get_or_create_partner(
                    sender_id=conversation.sender_id,
                    company_id=chat.company_id)
                mail_channel = conversation.create_live_chat_channel(
                    conversation.sender_id.partner_id)
                mail_channel.write({'name': mail_channel.name})
                subtype = self.env['mail.message.subtype'].search(
                    [('default', '=', True)], limit=1)
                mail_channel.message_post(
                    author_id=conversation.sender_id.partner_id.id,
                    body=_('%(name)s joined you',
                           name=conversation.sender_id.name),
                    message_type='comment',
                    subtype_id=subtype.id, )
        return conversation

    def prepare_echat_message_data(self, text):
        massage_id = self.echat_out_message(text=text)
        if self.chat_id.echat_messanger in ('viber', 'whatsapp'):
            body = {
                "number": self.chat_id.echat_mobile_phone,
                "message": {
                    "id": str(massage_id.id) if massage_id else str(
                        uuid.uuid4()),
                    "text": text,
                },
                "contact": {
                    "number": self.sender_id.echat_mobile_phone
                }
            }
        else:
            body = {
                "user": {
                    "number": self.chat_id.echat_mobile_phone},
                "message": {
                    "id": massage_id.id if massage_id else str(
                        uuid.uuid4()),
                    "text": text},
                "receiver": {
                    "id": self.name,
                    "phone": self.sender_id.echat_mobile_phone,
                }
            }
        return body

    def send_message(self, text, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'echat':
            return super().send_message(text, **kwargs)
        try:
            base_url = self.chat_id._get_echat_url()
            if self.chat_id.echat_messanger in ('viber', 'whatsapp'):
                endpoint = '/messages/send'
                header_key = 'Api-Key'
            else:
                endpoint = '/SendMessage.php'
                header_key = 'API'

            url = f"{base_url}{endpoint}"
            headers = {header_key: self.chat_id.echat_api_token}

            body = self.prepare_echat_message_data(text)
            # pylint: disable=E8106
            response = requests.request(
                method='post', url=url, json=body, headers=headers)
            if 200 <= response.status_code < 300:
                self.echat_create_log(name='OUT', body=body)
                self.is_echat_send = True
        except Exception as e:
            _logger.debug(e)
        return None

    def prepare_echat_file_data(self, url):
        massage_id = self.echat_out_message(text={'media': url})
        if self.chat_id.echat_messanger in ('viber', 'whatsapp'):
            body = {
                "number": self.chat_id.echat_mobile_phone,
                "message": {
                    "id": str(massage_id.id) if massage_id else str(
                        uuid.uuid4()),
                    "text": url,
                    "type": 'media',
                },
                "contact": {
                    "number": self.sender_id.echat_mobile_phone,
                }
            }
        else:
            body = {
                "user": {
                    "number": self.chat_id.echat_mobile_phone},
                "message": {
                    "id": massage_id.id if massage_id else str(
                        uuid.uuid4()),
                    "text": url,
                    "type": 'media',
                },
                "receiver": {
                    "id": self.name,
                    "phone": self.sender_id.echat_mobile_phone,
                }
            }
        return body

    def send_file(self, files, **kwargs):
        self.ensure_one()
        if self.chat_id.messenger_id.provider != 'echat':
            return super().send_file(files, **kwargs)
        for file in files:
            if file and file.datas:
                file_url = self.echat_get_attachment_url(attachment=file)
                try:
                    body = self.prepare_echat_file_data(file_url)

                    base_url = self.chat_id._get_echat_url()
                    if self.chat_id.echat_messanger in ('viber', 'whatsapp'):
                        endpoint = '/messages/send'
                        header_key = 'Api-Key'
                    else:
                        endpoint = '/SendMessage.php'
                        header_key = 'API'

                    url = f"{base_url}{endpoint}"
                    headers = {header_key: self.chat_id.echat_api_token}

                    # pylint: disable=E8106
                    response = requests.request(
                        method='post', url=url, json=body, headers=headers)
                    if response:
                        self.echat_create_log(name='OUT', body=body)
                except Exception as e:
                    _logger.debug(e)
        return None

    def echat_get_attachment_url(self, attachment):
        burl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if self.chat_id.is_developer_mode and self.chat_id.echat_developer_url:
            burl = self.chat_id.echat_developer_url.strip()
        token = attachment.generate_access_token()
        token = token[0] if token else ''
        url = '{}/web/content/ir.attachment/{}/datas?access_token={}'.format(
            burl, attachment.id, token)
        return url

    def echat_out_message(self, text=False):
        self.ensure_one()
        sender = self.env['kw.chatbot.sender'].search([
            ('name', '=', 'E-Chat')], limit=1)
        return self.env['kw.chatbot.message'].sudo().create({
            'conversation_id': self.id, 'is_bot_message': True,
            'sender_id': sender.id, 'text': text,
            'name': 'None', })

    def echat_create_log(self, name=False, body=False):
        self.ensure_one()
        self.env['kw.chatbot.log'].create({
            'name': name,
            'messenger_id': self.chat_id.messenger_id.id,
            'body': body,
            'chat_id': self.chat_id.id,
            'dialog_id': self.dialog_id.id,
            'sender_id': self.sender_id.id,
            'conversation_id': self.id,
        })

    def echat_upload_url_image(self, message):
        messenger = self.chat_id.echat_messanger
        if messenger in ('viber', 'whatsapp'):
            url = message.get('file')
        elif messenger == 'telegram':
            url = message.get('media')
        else:
            url = None
        if not url:
            return False
        try:
            # pylint: disable=E8106
            r = requests.get(url, allow_redirects=True)
            data = r.content
            mimetype = r.headers.get('content-type')
            data = base64.b64encode(data)
            data = data.decode('utf-8')
            filename = message.get('file_name') or url.split('/')[-1] or 'File'
        except Exception as e:
            _logger.debug(e)
            return False
        attachment = self.env['ir.attachment'].sudo().create({
            'name': filename, 'datas': data,
            'mimetype': mimetype, 'res_model': 'mail.compose.message'})
        if attachment:
            self.connect_live_chat(attachment=attachment)
            return attachment
        return False

    def echat_get_response(self, jsonrequest):
        message = jsonrequest['message']
        text = message.get('text')
        self.ensure_one()
        if self.dialog_id.bots_type == 'is_consultant_bot':
            if text in ['/start', '/end']:
                return None
            if text:
                live_chat_mess_id = self.connect_live_chat(text=text)
                if live_chat_mess_id:
                    self.write({'is_echat_send': True})
            if message.get('file') or message.get('media'):
                live_chat_attach_id = self.echat_upload_url_image(
                    message=message)
                if live_chat_attach_id:
                    self.write({'is_echat_send': True})
        if self.is_echat_send:
            return None
        return False


class Message(models.Model):
    _inherit = 'kw.chatbot.message'

    echat_id = fields.Char()
