{
    "name": "Calendar Improvements for Footbik",
    "category": "Uncategorized",
    "version": "17.0.1.0.1",
    "license": "LGPL-3",
    "depends": [
        'base',

        'oleg_weba_footbik'
    ],
    "data": [
        'views/class_trainings_views.xml'
    ],

    "assets": {
        'web.assets_backend': [
            'footbik_training_calendar/static/src/views/calendar/calendar_trainings/**/*',
        ]
    },

    "installable": True,
}
