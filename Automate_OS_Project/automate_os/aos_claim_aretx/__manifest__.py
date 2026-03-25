{
    'name': 'Sale Order Technician',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Add Technician field in Sale Order',
    'description': 'Adds a Technician field to the Sale Order form view.',
    'depends': ['sale','aos_sms_aretx'],
    'data': [
        'security/claim_report_security.xml',
        "security/ir.model.access.csv",
        'data/custom_sale_report_action.xml',
        "views/claim_report_views.xml",
        #'views/sale_order_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            #'aos_claim_aretx/static/src/scss/expense.scss',
            #'aos_claim_aretx/static/src/js/custom.js',

        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
