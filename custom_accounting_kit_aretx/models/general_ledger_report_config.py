from odoo import models, fields, api


class GeneralLedgerReportConfig(models.Model):
    _name = 'general.ledger.report.config'
    _description = 'General Ledger Report Configuration'
    _rec_name = "name"
    _check_company_auto = True

    name = fields.Char(string="Configuration Name", required=True, default="Default Configuration")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    # 🆕 Fields for customization (Matching the OWL component's logic)
    show_journal = fields.Boolean(string="Show Journal (Move Name)", default=True)
    show_date = fields.Boolean(string="Show Date", default=True)
    show_communication = fields.Boolean(string="Show Communication (Ref/Label)", default=True)
    show_partner = fields.Boolean(string="Show Partner", default=True)
    show_currency = fields.Boolean(string="Show Currency", default=True)
    show_debit = fields.Boolean(string="Show Debit", default=True)
    show_credit = fields.Boolean(string="Show Credit", default=True)
    show_balance = fields.Boolean(string="Show Balance", default=True)

    _sql_constraints = [
        ('unique_company_config', 'unique(company_id)',
         'Only one General Ledger Configuration is allowed per company.'),
    ]

    # 🆕 Updated method to return all field values
    @api.model
    def get_active_config(self):
        # Search for existing config for the current company, filtered by company_id
        config = self.search([('company_id', '=', self.env.company.id)], limit=1)

        if not config:
            # Create a new one if none exists
            config = self.create({'company_id': self.env.company.id, 'name': 'Default Configuration'})

        # Return the ID and the fields needed by the OWL component
        return {
            'id': config.id,
            'show_journal': config.show_journal,
            'show_date': config.show_date,
            'show_communication': config.show_communication,
            'show_partner': config.show_partner,
            'show_currency': config.show_currency,
            'show_debit': config.show_debit,
            'show_credit': config.show_credit,
            'show_balance': config.show_balance,
        }