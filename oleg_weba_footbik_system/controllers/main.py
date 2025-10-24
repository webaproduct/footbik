from datetime import datetime
import logging

from odoo import http
from odoo.tools import json
from odoo.http import request


_logger = logging.getLogger(__name__)


KEY_MODEL = {
    "campaign_id": "utm.campaign",
    "medium_id": "utm.medium",
    "source_id": "utm.source",
    "utm_term_id": "utm.term",
    "utm_content_id": "utm.content",
    "medium2_id": "utm.medium",
    "source2_id": "utm.source",
}


class IntegrationSite(http.Controller):

    """
    {
        "data": {
            "parent_name": "Parent name",
            "child_name": "Child name",
            "email": "test@test.com",
            "phone": "0123456789",
            "city": "Kyiv",
            "birthday": "04-08-2025",

            "utm": {
                "campaign_id": "utm_campaign",
                "medium_id": "utm_medium",
                "source_id": "utm_source",
                "utm_term_id": "utm_term",
                "utm_content_id": "utm_content",
                "medium2_id": "medium2_id",
                "source2_id": "source2_id",
            },
        }
    }
    """
    @http.route(route="/integration_site/create_lead", type="json", auth="user",
                methods=["POST"])
    def create_crm_lead(self, **kw):
        data = json.loads(request.httprequest.data).get("data")

        payload = {
            "name": f"{data['child_name']}, {data['phone']}",
            "type": "lead",
            "city": data["city"],
            "contact_name": data["child_name"],
            "email_from": data["email"],
            "email_parent": data["email"],
            "phone": data["phone"],
            "telephone_parent": data["phone"],
            "full_name_parent": data["parent_name"],
            "birthday": datetime.strptime(data["birthday"], "%d-%m-%Y"),

            "referred": request.httprequest.headers.get('Host')
        }

        payload.update(self._get_utm(data.get("utm", False)))

        lead = request.env["crm.lead"].sudo().create(payload)

        mes = f"CRM Lead is created: {lead.id} - {lead.name}"
        _logger.info(f"[Integration Site] {mes}")
        return {"success": True, "status": f"{mes}", "code": 200}

    def _get_utm(self, utm):
        if not utm:
            return {}

        result = {}
        for field_name, utm_name in utm.items():
            if utm_name:
                result[field_name] = self._search_create_utm(
                    KEY_MODEL[field_name], utm_name, utm)  # utm словарь только для
                # заполнения поля medium2_id в модели utm.source

        return result

    @staticmethod
    def _search_create_utm(model, utm_name, utm_dict):
        Model = request.env[model]

        utm = Model.search([("name", "=", utm_name)], limit=1)
        if not utm:
            if model == "utm.source":

                # Пробуем найти запись в utm.medium, находим только для ключа source2_id
                # т.к. ключ medium2_id уже обработан и запись создана, при обработке
                # ключа source_id в поле medium2_id будет записано False
                medium = request.env["utm.medium"].search([
                        ("name", "=", utm_dict.get("medium2_id"))], limit=1)
                utm = Model.create({
                    "name": utm_name,
                    "medium2_id": medium.id if medium else False,
                })
            else:
                utm = Model.create({"name": utm_name})

        return utm.id
