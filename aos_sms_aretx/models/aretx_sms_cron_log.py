# aos_sms_aretx/models/aretx_sms_cron_log.py

from odoo import models, fields


class AretxSmsCronLog(models.Model):
    _name = 'aretx.sms.cron.log'
    _description = 'SMS Cron Log'
    _order = 'create_date desc'

    res_model = fields.Char(string="Model")
    res_id = fields.Integer(string="Record ID")

    partner_id = fields.Many2one('res.partner', string="Customer")
    vehicle_id = fields.Many2one('vehicle.master.model', string="Vehicle")

    phone = fields.Char(string="Phone")
    template_id = fields.Many2one('custom.sms.templates', string="Template")

    message = fields.Text(string="Message")

    delivery_status = fields.Selection([
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ], default='failed', string="Delivery Status")

    msg_id = fields.Char(string="Message ID")
    error_message = fields.Text(string="Error Message")
