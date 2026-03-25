{
    'name': "Auto Stock Picking From Invoice",
    'version': '19.0.1.0.0',
    'summary': """Auto Stock Picking From Customer/Supplier Invoice""",
    'description': """This Module Enables To Create Stocks Picking From Customer/Supplier Invoice""",
    'author': 'areterix',
    'company': 'Areterix Technologies',
    'website': "https://www.areterix.com",
    'category': 'Accounting',
    'depends': ['base', 'account', 'stock', 'payment'],
    'data': [
        'views/invoice_stock_move_view.xml'
    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
