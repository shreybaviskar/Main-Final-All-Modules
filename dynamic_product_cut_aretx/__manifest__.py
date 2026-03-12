{
    'name': 'Dynamic Product Cut Aretx',
    'version': '1.0',
    'summary': '1D Dynamic Product Cutting Management',

    'author': 'Aretx',
    'category': 'Inventory',

    'depends': [
        'product',
        'stock',
    ],

    'data': [

        'security/ir.model.access.csv',

        # Product modification
        'views/product_template_views.xml',

        # Cutting screen
        'views/cut_process_views.xml',

    ],

    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': -99,
}