{
    "name": "oleg_weba_footbik_system",
    "summary": "",
    "author": "Oleg (Weba)",
    "website": "https://weba.com.ua/",
    "category": "Uncategorized",
    "version": "17.0.21.2.0",
    "license": "LGPL-3",
    "depends": ["contacts", "hr", "crm", "oleg_weba_footbik",
                "utm", "subscription_oca", "calendar", "sale",
                "purchase", "sale_crm", "crm_iap_enrich", "account",
                "kw_checkbox"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",

        "views/res_partner_views.xml",
        "views/crm_lead_views.xml",
        "views/utm_source_views.xml",
        "views/skills_views.xml",
        "views/sale_subscription_views.xml",
        "views/sale_order_views.xml",
        "views/model_for_utm_views.xml",
        "views/frozen_subscription_views.xml",
        "views/account_move_views.xml",
        "views/product_template_views.xml",

        "views/class_training_views.xml",
        "views/class_attendance_views.xml",

        "wizard/wizard_frozen_subscription_views.xml",

        "data/utm_medium_data.xml",
        "data/utm_source_data.xml",

        "data/cron_sale_subscription.xml",
        "data/cron_frozen_subscription.xml",
        "data/cron_calculate_age.xml",

        "data/cron_change_create_date_historical.xml",
    ],
    "installable": True,
}
