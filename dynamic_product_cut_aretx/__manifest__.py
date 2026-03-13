{
    'name': 'Dynamic Product Cut',
    'version': '1.0',
    'sequence': -99,
    'application': True,
    'depends': ['stock', 'product'],

    'data': [

        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/cut_process_views.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': -99,
}