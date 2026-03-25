from odoo import api, fields, models


class CustomContacts(models.Model):
    _inherit = "res.partner"

    sms_history = fields.One2many('aretx.sms.composer', 'partner_id', string="SMS History", domain="[('partner_id','=',id)]", readonly=True, ondelete='restrict')
    mobile = fields.Char(string="Mobile",related="opportunity_ids.mobile", store=True, required=True,readonly=False)

    is_technician = fields.Boolean(string="Is Technician", default=False)

   

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    
    mobile = fields.Char(string="Mobile")



