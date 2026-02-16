# -*- coding: utf-8 -*-
{
    'name': "Sms Templates",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': 'areterix 2.0',
    'sequence': -100,
    'website': "https://areterix.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base','product','aos_vehicle_aretx','contacts','crm'],

    # always loaded
    'data': [
        # 'data/sms_cron.xml',
        'security/ir.model.access.csv',
        'wizard/aretx_sms_composer_views.xml',
        'views/views.xml',
        'views/aretx_sms_cron_log_views.xml',
        'views/setting.xml',
        'views/contacts.xml',
        'views/product_template.xml',
        'views/sms_history_customer.xml',
    ],
    # only loaded in demonstration mode
    'installable': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            # 'aretx_sms_integration/static/src/js/fields_aretxphone_widget.js',
            # 'aretx_sms_integration/static/src/js/fields_sms_widget.js',
            # 'aretx_sms_integration/static/src/components/*/*.js',
            # 'aretx_sms_integration/static/src/models/*/*.js',
        ]
    },
    'application': True,
   # 'demo': [
    #    'demo/demo.xml',
    #],
}
