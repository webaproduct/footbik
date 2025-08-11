# -*- coding: utf-8 -*-
{
    'name': "Looker Studio Connector",

    'summary': """
The Odoo to Looker Connector seamlessly integrates your Odoo ERP data with Google Looker Studio, enabling dynamic dashboards, interactive reports, and robust analytics. It supports various looker data sources, charts, graphs, and bar graphs to monitor KPIs with slicers for filtering. Compatible with Power BI Cloud and Data Studio, it features scheduled data refresh via a secure data gateway and includes forecasting, prediction, and comprehensive analytic analysis.
       """,

    'description': """
        	Looker Studio Connector Module for Odoo
    """,

    'author': "TechFinna",
    'website': "https://techfinna.com/looker-odoo-connector/",
    'category': 'Connector',
    'price': 449,
    'currency': 'USD',
    'version': '2.0.3',
    'installable': True,
    'live_test_url': 'https://techfinna.com/looker-odoo-connector',
    'support': "info@techfinna.com",
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
    'depends': ['base', 'web'],

    # any module necessary for this one to work correctly
    'images': ['static/description/banner.png'],
    "external_dependencies": {"python": ["pip"]},

    # always loaded
    'data': [
        'views/settings.xml',

    ],
    'assets': {
        'looker_connector.ass': [
            'looker_connector/views/sty.css'
        ]
    },

    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    "application": True,
    "installable": True,

}

