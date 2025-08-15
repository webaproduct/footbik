{
    'name': 'Chatbot E-Chat',
    'version': '17.0.2.1.5',
    'license': 'OPL-1',
    'category': 'Extra Tools',
    'summary': 'Adds E-Chat connector '
               'an E-Chat specific functionality',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'depends': [
        'kw_chatbot',
    ],
    'data': [

        'security/ir.model.access.csv',
        'data/sender.xml',

        'views/chat_views.xml',
        'views/sender_views.xml',
        'views/res_partner_views.xml',
        'wizard/conversation_wizard.xml',

    ],
    'installable': True,
    'images': [
        'static/description/icon.png',
    ],
}
