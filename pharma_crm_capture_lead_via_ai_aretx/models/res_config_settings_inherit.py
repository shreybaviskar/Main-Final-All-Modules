from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gemini_api_key = fields.Char(
        string="Gemini API Key",
        config_parameter="gemini.api.key",
        help="API key used for Gemini AI integration"
    )
