{
    'name': 'Remove Areterix Branding',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Add Technician field in Sale Order',
    'description': 'Adds a Technician field to the Sale Order form view.',
    'depends': ['base','web'],
    "data": [
         'views/login_page.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'aos_areterix_branding_aretx/static/src/scss/expense.scss',
            'aos_areterix_branding_aretx/static/src/js/custom.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
