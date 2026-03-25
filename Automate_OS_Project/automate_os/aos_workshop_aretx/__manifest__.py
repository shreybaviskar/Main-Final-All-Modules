{
    'name': 'Aretx WorkShop',
    'version': '19.0.1.0.0',
    'summary': 'Vehicle Details for Workshop',
    'category': 'Industry',
    'author': 'Aretrix',
    'sequence': -200,
    'depends': [ 'sale','base','aos_vehicle_aretx'],
    'data': [
        'views/workshop_views.xml',
        'views/custom_invoice_report.xml',
        'views/custom_sale_order_report.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}