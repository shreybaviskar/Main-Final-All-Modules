{
    "name": "Odoo WhatsApp Invoice | WhatsApp Cloud API | Odoo V19 Community Edition",
    "version": "1.0",
    "author": "TechUltra Solutions Private Limited",
    "category": "Accounting",
    "live_test_url": "https://www.techultrasolutions.com/blog/news-2/odoo-whatsapp-integration-a-boon-for-business-communication-25",
    "company": "TechUltra Solutions Private Limited",
    "website": "https://www.techultrasolutions.com/",
    "price": 19,
    "currency": "USD",
    "summary": "whatsapp invoice all in one invoicing Solutions which allows user to notify to the customer for the invoices and payment",
    "description": """
        whatsapp invoice whatsapp all in one solutions will allow user to send the notifications about the customer invoices and updates.
    """,
    "depends": ["aos_whatsapp_base_aretx", "account","sale"],
    "data": [
        "security/invoice_security.xml",
        "data/wa_template.xml",
        "views/wa_stock_picking.xml",
        "views/account_move.xml",
        "views/sale.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "OPL-1",
    "images": ["static/description/main_screen.gif"],
    # 'post_init_hook': '_set_image_in_company',
}
