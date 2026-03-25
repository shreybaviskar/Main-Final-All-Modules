# -*- coding: utf-8 -*-
{
    'name': "Vehicle",

    'summary': """
        Summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': 'areterix',
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '19.0.0.1',

    # any module necessary for this one to work correctly
    # 'depends': ['mail', 'contacts', 'sale', 'base','subscription_package'],
    'depends': ['mail', 'contacts', 'sale', 'base','project','account'],
    'sequence': -100,


    # always loaded
    'data': [
        'security/aretx_vehicle_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/vehicle_brand_view.xml',
        'views/vehicle_type_view.xml',
        'views/vehicle_color_view.xml',
        'views/vehicle_model_view.xml',
        'views/vehicle_master_view.xml',
        'views/contacts.xml',
        'views/invoice_inherit_view.xml',
        'views/sale_inherit_view.xml',
        'views/configuration_view.xml',
        'reports/report_invoice_document.xml',
        'reports/report_sale_document.xml',

    ],

    'installable': True,
    'auto_install': False,
    'assets': {},
    'application': True,
    'license': 'LGPL-3'
}
