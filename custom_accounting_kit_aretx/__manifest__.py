{
    'name': 'General Ledger Report',
    'version': '1.0',
    'license': 'LGPL-3',
    'summary': 'Custom General Ledger Report',
    'category': 'Accounting',
    'author': 'Areterix Technologies',
    'website': 'https://www.areterix.com/',
    'depends': ['account', 'web'],
    'data': [
        'security/ir.model.access.csv',

        'data/pdf_paper_format.xml',

        'views/general_ledger_owl_action.xml',
        'views/general_ledger_pdf_template.xml',
        'views/general_ledger_report_config_views.xml',
    ],
    "assets": {
        "web.assets_backend": [
            "custom_accounting_kit_aretx/static/src/js/general_ledger_report_owl.js",
            "custom_accounting_kit_aretx/static/src/xml/general_ledger_report.xml",
            "custom_accounting_kit_aretx/static/src/css/general_ledger_report.css",
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}