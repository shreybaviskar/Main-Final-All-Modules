{
    'name': 'Driver Transfer Funds',
    'version': '19.0.0.1',
    'summary': 'Transfer funds between journals from the journal dashboard',
    'description': """
        Adds a "Transfer Funds" button to each journal's kanban card on the
        Accounting dashboard.  Clicking it opens a wizard that creates a posted
        internal transfer payment between two journals.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'category': 'Accounting/Accounting',
    'license': 'LGPL-3',

    'depends': [
        'account',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/transfer_fund_wizard_views.xml',
        'views/account_journal_view_inherit.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}