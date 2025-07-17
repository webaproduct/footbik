import logging

from odoo import http
from odoo.tools import json
from odoo.http import request


_logger = logging.getLogger(__name__)


# {
#     "data": {
#         "parent_name": "Parent name",
#         "child_name": "Child name",
#         "email": "test@test.com",
#         "phone": "0123456789",
#         "city": "Ukraine",
#         "age": 12,
#         "tag": "utm",
#     }
# }


class IntegrationSite(http.Controller):

    @http.route(route="/integration_site/create_lead", type="json", auth="user",
                methods=["POST"])
    def create_crm_lead(self, **kw):
        data = json.loads(request.httprequest.data).get("data")

        lead = request.env["crm.lead"].sudo().create({
            "name": f"{data['child_name']}, {data['phone']}",
            "type": "lead",
            "city": data["city"],
            "contact_name": data["child_name"],
            "email_from": data["email"],
            "email_parent": data["email"],
            "phone": data["phone"],
            "telephone_parent": data["phone"],
            "full_name_parent": data["parent_name"],
            "description": data["age"],
        })
        mes = f"CRM Lead is created: {lead.id} - {lead.name}"
        _logger.info(f"[Integration Site] {mes}")
        return {"success": True, "status": f"{mes}", "code": 200}
