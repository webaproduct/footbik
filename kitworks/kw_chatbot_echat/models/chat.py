import logging

import requests
from odoo import models, fields

_logger = logging.getLogger(__name__)


class Chat(models.Model):
    _inherit = 'kw.chatbot.chat'

    echat_api_token = fields.Char()
    echat_mobile_phone = fields.Char(
        string='Mobile Phone')
    echat_integration = fields.Selection(
        selection=[('api', 'API'), ('amo_crm', 'amoCRM'),
                   ('bitrix24', 'Bitrix24'), ('trend_crm', 'TrendCRM'),
                   ('key_crm', 'KeyCRM'), ('plan_fix', 'PlanFix'),
                   ('apix_drive', 'Apix-Drive'), ('onebox', 'OneBox'), ],
        default='api', )
    echat_end_tarif = fields.Char(
        string='End Tarif', readonly=True, )
    echat_connection_status = fields.Char(
        string='Connection Status', readonly=True, )

    echat_crm_user_id = fields.Many2one(
        comodel_name='res.users', string='Salesperson')
    echat_crm_team_id = fields.Many2one(
        comodel_name='crm.team', string='Sales Team')
    echat_crm_type = fields.Selection([
        ('lead', 'Lead'), ('opportunity', 'Opportunity')],
        default='opportunity', string='Type')
    echat_messanger = fields.Selection(
        selection=[
            ('viber', 'Viber'),
            ('telegram', 'Telegram'),
            ('whatsapp', 'WhatsApp'),
        ],
        default='viber', )
    echat_incoming_webhook = fields.Char(
        compute='_compute_echat_webhook', readonly=True, )
    echat_outgoing_webhook = fields.Char(
        compute='_compute_echat_webhook', readonly=True, )

    echat_developer_url = fields.Char()

    def _compute_echat_webhook(self):
        for obj in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param(
                'web.base.url')
            if obj.is_developer_mode and obj.echat_developer_url:
                base_url = obj.echat_developer_url
            obj.echat_incoming_webhook = "{}/kw_chatbot/echat/incoming/" \
                                         "{}".format(base_url, obj.id)
            obj.echat_outgoing_webhook = "{}/kw_chatbot/echat/outgoing/" \
                                         "{}".format(base_url, obj.id)

    def _get_echat_url(self):
        url_map = {
            'telegram': 'https://telegram.e-chat.tech/api',
            'viber': 'https://e-chat.tech/api/viber/v2',
            'whatsapp': 'https://e-chat.tech/api/whatsapp/v1',
        }
        return url_map.get(self.echat_messanger, 'https://e-chat.tech/api')

    # pylint: disable=R1710
    def echat_create_chat(self):
        base_url = self._get_echat_url()

        if self.echat_messanger in ('viber', 'whatsapp'):
            endpoint = "/channel/connect"
            header_key = 'api-key'
        else:
            endpoint = "/CreateChannel.php"
            header_key = 'API'

        url = f"{base_url}{endpoint}"
        headers = {header_key: self.echat_api_token}

        body = {
            "number": self.echat_mobile_phone,
            "integration": self.echat_integration,
        }
        # pylint: disable=E8106
        response = requests.request(method='post', url=url, json=body,
                                    headers=headers)
        if 200 <= response.status_code < 300:
            channel = response.json()
            self.write({
                'echat_connection_status': channel.get('description'),
                'echat_end_tarif': channel.get('end_tarif'), })
        else:
            self.write({'echat_connection_status': 'Error'})

    def echat_process_message(self, message, log):
        self.ensure_one()
        sender = self.env['kw.chatbot.sender'].sudo().get_or_create(
            messenger=self.messenger_id,
            echat_messanger=self.echat_messanger,
            json_data=message,
            sender=message.get('sender'),
        )
        conversation = self.env['kw.chatbot.conversation'].sudo(
        ).get_or_create(chat=self, message=message, sender=sender)
        log.sudo().write({
            'sender_id': sender.id, 'conversation_id': conversation.id, })
        echat_message = message.get('message')
        if echat_message:
            text = echat_message.get('text')
            m_data = {
                'echat_id': sender.echat_sender_id,
                'conversation_id': conversation.id,
                'sender_id': sender.id, 'text': text,
                'name': text, }
            conversation.last_activity_datetime = fields.Datetime.now()
            attach_id = conversation.echat_upload_url_image(echat_message)
            if attach_id:
                m_data.update({'attachment_ids': [(4, attach_id.id)]})
            else:
                conversation.echat_get_response(message)
            conversation.chatbot_message_id = \
                self.env['kw.chatbot.message'].sudo().create(m_data)

    def echat_process_call(self, jsonrequest, log):
        self.ensure_one()
        if jsonrequest.get('direction') == 'incoming':
            self.echat_process_message(
                message=jsonrequest, log=log)
