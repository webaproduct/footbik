{
    'name': 'CheckBox',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'category': 'Point of Sale',
    'license': 'OPL-1',
    'version': '17.0.2.8.9',
    'summary': 'Checkbox, Чекбокс, Україна, Модулі для України',

    'depends': ['base', 'web', 'product', 'account', ],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'data/checkbox_product_category.xml',
        'data/ir_cron_data.xml',

        'views/menu_view.xml',
        'views/log_view.xml',
        'wizard/x_report_wizard_views.xml',
        'wizard/service_receipt_wizard_views.xml',
        'wizard/account_payment_register_views.xml',
        'views/receipt_views.xml',
        'views/cashier_views.xml',
        'views/cash_registers_views.xml',
        # 'views/receipt_views.xml',
        'views/res_company_views.xml',
        'views/shift_views.xml',
        'views/organization_views.xml',
        'views/res_users_views.xml',
        'views/product_category_checkbox_views.xml',
        'views/offline_code_views.xml',
        'views/tax_views.xml',
        'views/z_reports_views.xml',
        'views/x_reports_views.xml',

        'views/account_view.xml',
        'views/account_tax_views.xml',

        'views/product_template_views.xml',
        'views/product_category_views.xml',


        'views/account_invoice_view.xml',
        'views/account_payment_view.xml',

        'report/reporting.xml',
        'report/z_report.xml',
        'report/x_report.xml',

    ],
    'installable': True,
    'application': True,

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],

    'price': 250,
    'currency': 'EUR',
}
