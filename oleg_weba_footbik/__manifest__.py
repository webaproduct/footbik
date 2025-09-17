{
    "name": "oleg_weba_footbik",
    "summary": "",
    "author": "Oleg (Weba)",
    "website": "https://weba.com.ua/",
    "category": "Uncategorized",
    "version": "17.0.11.0.1",
    "license": "LGPL-3",
    "depends": ["contacts", "hr", "subscription_oca"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",

        "views/menu_view.xml",
        "views/class_program_views.xml",
        "views/class_age_views.xml",
        "views/class_color_group_views.xml",
        "views/class_location_views.xml",
        "views/class_group_views.xml",
        "views/class_training_views.xml",
        "views/class_attendance_views.xml",
        "views/class_type_numbering.xml",

        "views/res_partner_views.xml",

        # "data/data_res_partner.xml",  # TODO
    ],

    "assets": {
        "web.assets_backend": [
            "oleg_weba_footbik/static/src/css/kanban_styles.css",
        ],
    },

    "installable": True,
}
