{
    "name": "oleg_weba_footbik_system",
    "summary": "",
    "author": "Oleg (Weba)",
    "website": "https://weba.com.ua/",
    "category": "Uncategorized",
    "version": "17.0.8.2.0",
    "license": "LGPL-3",
    "depends": ["contacts", "hr", "crm", "oleg_weba_footbik",
                "utm", "subscription_oca", "calendar", "sale",
                "purchase", "sale_crm"],
    "data": [
        "security/ir.model.access.csv",

        "views/res_partner_views.xml",
        "views/crm_lead_views.xml",
        "views/utm_source_views.xml",
        "views/skills_views.xml",
        "views/sale_subscription_views.xml",
        "views/sale_order_views.xml",
        "views/model_for_utm_views.xml",

        "data/utm_medium_data.xml",
        "data/utm_source_data.xml",

        "data/cron_sale_subscription.xml",
    ],
    "installable": True,
}
