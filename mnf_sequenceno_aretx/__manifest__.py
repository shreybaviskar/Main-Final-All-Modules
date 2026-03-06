# -*- coding: utf-8 -*-
{
    'name': 'MNF Sequence No ARETX',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Adds Serial Number (Sr.) column before Description in Invoice PDF',
    'description': """
        This module adds a 'Sr.' (Serial Number) column before the Description column
        in the invoice PDF report. The serial number auto-increments for each product
        line in the invoice.
    """,
    'author': 'ARETX',
    'website': 'https://www.aretx.com',
    'depends': [
        'account',
        'aos_workshop_aretx',
    ],
    'data': [
        'views/invoice_report_inherit.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
