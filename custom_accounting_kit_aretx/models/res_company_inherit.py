# models/res_company_inherit.py
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def get_current_company_country(self):
        # Use sudo() to avoid access issues
        company = self.env.company.sudo()
        return {
            "id": company.id,
            "name": company.name,
            "country_code": company.account_fiscal_country_id.code or False,
        }

    @api.model
    def get_current_company_info(self):
        company = self.env.company.sudo()

        return {
            "id": company.id,
            "name": company.name,
            "currency_id": company.currency_id.id,
            "email": company.email or False,
            "phone": company.phone or False,
            "font": company.font,
            "report_header": company.report_header,
            "report_footer": company.report_footer,
            "company_details": company.company_details,
            "logo_web": company.logo_web,
            "currency_name": company.currency_id.name,
            "country_code": company.account_fiscal_country_id.code or False,
            "vat": company.partner_id.vat,
        }