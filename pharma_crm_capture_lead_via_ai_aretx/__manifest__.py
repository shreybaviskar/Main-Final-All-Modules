{
    'name': 'Capture Lead via Gemini AI',
    'version': '19.0.0.1',
    'license': 'LGPL-3',
    'summary': 'Create CRM leads by capturing images or uploading files via Google Gemini',
    'description':
        """
        This module allows capturing CRM leads by uploading images or PDF files.
        It uses Google Gemini AI to extract structured information from images/PDFs
        and automatically fills CRM lead fields.
        
        Required Python packages (install via pip):
        - google-generativeai
        - pillow
        - pdfplumber
        - python-dotenv
        
        Configure GEMINI_API_KEY in .env file.
        """,
    'category': 'Pharma',
    'author': 'Areterix Technologies',
    'website': 'https://www.areterix.com/',
    'depends': ['base', 'web', 'sale_management', 'purchase', 'stock', 'crm'],
    'data': [
        #Security

        #Views:
        'views/crm_lead_inherit_views.xml',
        'views/res_config_settings_inherit_views.xml',
    ],
    "assets": {

    },
    'images': ["static/description/icon.png"],
    'installable': True,
    'application': False,
    'auto_install': False,
}