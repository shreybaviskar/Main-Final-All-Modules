from odoo import models, fields

class WaCronLog(models.Model):
    _name = 'wa.cron.log'
    _description = 'WhatsApp Cron Log'
    _order = 'date desc'
    _rec_name = 'phone'

    provider_id = fields.Many2one('provider', 'Provider', readonly=True)
    author_id = fields.Many2one('res.partner', 'Author', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Recipient', readonly=True)
    phone = fields.Char(string="Whatsapp Number", readonly=True)
    # phn_no = fields.Char('Phone Number')
    message = fields.Char('Message', readonly=True)
    type = fields.Selection([
        ('in queue', 'In queue'),
        ('sent', 'Sent'),
        ('delivered', 'delivered'),
        ('received', 'Received'), ('read', 'Read'), ('fail', 'Fail')], string='Type', default='in queue', readonly=True)
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'wa_cron_log_attachment_rel',  # DIFFERENT TABLE
        'cron_log_id',  # DIFFERENT COLUMN
        'attachment_id',
        string='Attachments'
    )
    message_id = fields.Char("Message ID", readonly=True)
    mail_message_id = fields.Many2one('mail.message')
    fail_reason = fields.Char("Fail Reason", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', related="provider_id.company_id")
    allowed_company_ids = fields.Many2many(
        comodel_name='res.company', string="Allowed Company",
        default=lambda self: self.env.company)
    date = fields.Datetime('Date', default=fields.Datetime.now, readonly=True)
    model = fields.Char('Related Document Model', index=True, readonly=True)
    active = fields.Boolean('Active', default=True)
    rec_id = fields.Integer("Related Model ID", readonly=True)


    vehicle_id = fields.Many2one(
        'vehicle.master.model',
        string="Vehicle",
        ondelete='set null'
    )

    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ], required=True)

    api_response = fields.Text(string="API Response")

