{
    'name': 'CheckBox in Point of Sale',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'category': 'Customizations',
    'license': 'OPL-1',
    'version': '17.0.2.4.3',
    'summary': '''Checkbox, CheckboxPOS, Point of Sale, Чекбокс,
Україна, Модулі для України''',

    'depends': ['kw_checkbox', 'pos_hr'],

    'data': [
        'security/ir.model.access.csv',

        'wizard/wizard_offline_mode_view.xml',

        'views/checkbox_category_views.xml',
        'views/cash_register_views.xml',
        'views/pos_config_views.xml',
        'views/shift_views.xml',
        'views/pos_order_view.xml',
        'views/pos_session_views.xml',
        'views/pos_payment_method_view.xml',
        'views/point_of_sale_dashboard.xml',
        'views/pos_excise.xml',
        'views/product_view.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'kw_checkbox_pos/static/src/js/models.js',
            'kw_checkbox_pos/static/src/js/Order.js',
            'kw_checkbox_pos/static/src/js/receipt_screen.js',
            'kw_checkbox_pos/static/src/js/EditExciseInput.js',
            'kw_checkbox_pos/static/src/js/EditListExcise.js',
            'kw_checkbox_pos/static/src/js/excise_popup_handler.js',
            'kw_checkbox_pos/static/src/js/Orderline.js',
            'kw_checkbox_pos/static/src/js/Screens/'
            'PaymentScreen/PaymentScreen.js',
            'kw_checkbox_pos/static/src/xml/'
            'Screens/ReceiptScreen/OrderReceipt.xml',
            'kw_checkbox_pos/static/src/xml/OrderLineExcise.xml',
            'kw_checkbox_pos/static/src/xml/EditExciseInput.xml',
            'kw_checkbox_pos/static/src/xml/EditListExcise.xml',
        ],
    },
    'price': 50,
    'currency': 'EUR',
}
