# -*- coding: utf-8 -*-

from odoo import models, fields, _, api, Command
from odoo.exceptions import UserError,ValidationError

import logging
_logger = logging.getLogger(__name__)

class custom_sms_templates(models.Model):
    _name = 'custom.sms.templates'
    _description = 'custom_sms_templates.custom_sms_templates'


    name = fields.Char(string='Sms Title', tracking=True)
    # value = fields.Integer()
    # value2 = fields.Float(compute="_value_pc", store=True)
    description = fields.Text(string='Sms Content (Use "%bill_amount%" For Bill Amount/ Use "%customer%" For Customer/ Use "%vehicle%" For Vehicle/ Use "%branch%" For Branch/ Use "%service%" For Service)', tracking=True)

    @api.depends('value')
    def _value_pc(self):
        for record in self:
            record.value2 = float(record.value) / 100

class custom_sms_setting(models.Model):
    _name = 'custom.sms.setting'
    _description = 'custom_sms_setting.custom_sms_setting'
    _rec_name = 'gsm_sendername'
    # SMS API SETTINGS
    account_type = fields.Selection([('2', 'Transaction'), ('1', 'Promotion'), ('3', 'OPT-IN')],'Select Account Type',default='2',required="1")
    send_url = fields.Char(string='Send URL', tracking=True)
    deliver_url = fields.Char(string='Deliver URL', tracking=True)
    balance_url = fields.Char(string='Balance URL', tracking=True)
    schedule_create_url = fields.Char(string='Schedule Create URL', tracking=True)
    schedule_send_url = fields.Char(string='Schedule Send URL', tracking=True)
    userid = fields.Char(string='UserId', tracking=True)
    userpassword = fields.Char(string='User Password', tracking=True)
    gsm_sendername = fields.Char(string='GSM(SENDER NAME)', tracking=True)
    message_type = fields.Integer(string='Message Type', tracking=True, default='0') #0-Default Message,1-Flash Message,2-Unicode Message


    # URL MAPPER
    userid_map = fields.Char(string='UserId Map', tracking=True)
    userid_password_map = fields.Char(string='User Password Map', tracking=True)
    gsm_map = fields.Char(string='GSM Map', tracking=True)
    phonenumber_map = fields.Char(string='Phone Number Map', tracking=True)
    msg_map = fields.Char(string='Message(Text) Map', tracking=True)
    sent_msg_id_map = fields.Char(string='Sent Message ID Map', tracking=True)
    log_date_map = fields.Char(string='Log Date(Sent Message Date) Map', tracking=True)
    account_type_map = fields.Char(string='Account Type Map', tracking=True, default='AccountType')
    message_type_map = fields.Char(string='Message Type Map', tracking=True, default='MessageType')


# class product_product(models.Model):
#     _inherit = "product.product"
#
#     @api.onchange('default_sms_template', 'default_email_template', 'from_order_date_number_of_days', 'reminder_day_month_year')
#     def _change_number_of_days_reminder_sms(self):
#         self.product_tmpl_id._change_number_of_days_reminder_sms()

class product_template(models.Model):
    _inherit = "product.template"

    # @api.model
    # def _compute_number_of_days_reminder_sms(self):
    #     set_value = 999
    #     for rec in self:
    #         if int(rec.from_order_date_number_of_days) > 0:
    #             set_value = int(rec.from_order_date_number_of_days)
    #     return int(set_value)


    default_sms_template = fields.Many2one('custom.sms.templates', string='Default SMS Template', tracking=True, store=True, help='This field is used send automation reminder')
    default_email_template = fields.Many2one('mail.template', string='Default Email Template', tracking=True, store=True, help='This field is used send automation reminder')
    from_order_date_number_of_days = fields.Integer('Number Of Days/Month/Year', help='This field is used send automation reminder from order date to this number of days/month/year', required=True, default=999)
    reminder_day_month_year = fields.Selection(selection=[('days', 'Days'), ('month', 'Month'), ('year', 'Year')], string='Select Reminder Days/Month/Year', store=True, help='This field is used send automation reminder from order date to this number of days/month/year', required=True, default='year')

    # @api.onchange('default_sms_template', 'default_email_template', 'from_order_date_number_of_days', 'reminder_day_month_year')
    # def _change_number_of_days_reminder_sms(self):
    #     set_value = 0
    #     for rec in self:
    #         if rec.default_sms_template.id is False and rec.default_email_template.id is False and rec.reminder_day_month_year is not False:
    #             rec.reminder_day_month_year = ''
    #
    #         if rec.default_sms_template.id is not False or rec.default_email_template.id is not False or rec.reminder_day_month_year is not False:
    #             if int(rec.from_order_date_number_of_days) <= 0:
    #                 set_value = 999
    #             else:
    #                 set_value = int(rec.from_order_date_number_of_days)
    #     self.from_order_date_number_of_days = int(set_value)

    # @api.model_create_multi
    # def create(self, vals):
    #     # print('vals::::::::::::',vals)
    #     # print('vals::::::::::::',vals[0])
    #     if len(vals) > 0 and 'default_sms_template' in vals[0] and vals[0]['default_sms_template'] is not False and 'reminder_day_month_year' in vals[0] and vals[0]['reminder_day_month_year'] not in ['days', 'month', 'year'] or len(vals) > 0 and 'default_email_template' in vals[0] and vals[0]['default_email_template'] is not False and 'reminder_day_month_year' in vals[0] and vals[0]['reminder_day_month_year'] not in ['days', 'month', 'year']:
    #         raise ValidationError(_('Select Reminder Days/Month/Year Field!'))
    #     p_id = super(product_template, self).create(vals)
    #     # self.env['aretx.sms.composer']._delivery_status_check()
    #     # self.env['aretx.sms.composer']._automatic_reminder()
    #     return p_id

    # def write(self, vals):
    #     # print('vals::::::::::::',vals)
    #     # print('self::::::::::::',self.)
    #     if 'default_sms_template' in vals and vals['default_sms_template'] is not False and 'reminder_day_month_year' not in vals or 'default_email_template' in vals and vals['default_email_template'] is not False and 'reminder_day_month_year' not in vals:
    #         raise UserError('Select Reminder Days/Month/Year Field!')
    #     p_id = super(product_template, self).write(vals)
    #     # self.env['aretx.sms.composer']._delivery_status_check()
    #     # self.env['aretx.sms.composer']._automatic_reminder()
    #     return p_id


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def add_to_queue_mail(self, res_id, force_send=False, raise_exception=False, email_values=None, notif_layout=False):
        """ Generates a new mail.mail. Template is rendered on record given by
        res_id and model coming from template.

        :param int res_id: id of the record to render the template
        :param bool force_send: send email immediately; otherwise use the mail
            queue (recommended);
        :param dict email_values: update generated mail with those values to further
            customize the mail;
        :param str notif_layout: optional notification layout to encapsulate the
            generated email;
        :returns: id of the mail.mail that was created """

        # Grant access to send_mail only if access to related document
        for rec in self:
            Attachment = self.env['ir.attachment']  # TDE FIXME: should remove default_type from context

            # create a mail_mail based on values, without attachments
            values = rec.generate_email(res_id, ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
            values['recipient_ids'] = [Command.link(pid) for pid in values.get('partner_ids', list())]
            values['attachment_ids'] = [Command.link(aid) for aid in values.get('attachment_ids', list())]
            values.update(email_values or {})
            attachment_ids = values.pop('attachment_ids', [])
            attachments = values.pop('attachments', [])
            # add a protection against void email_from
            if 'email_from' in values and not values.get('email_from'):
                values.pop('email_from')
            # encapsulate body
            if notif_layout and values['body_html']:
                try:
                    template = self.env.ref(notif_layout, raise_if_not_found=True)
                except ValueError:
                    _logger.warning('QWeb template %s not found when sending template %s. Sending without layouting.' % (notif_layout, rec.name))
                else:
                    record = self.env[rec.model].browse(res_id)
                    model = self.env['ir.model']._get(record._name)

                    if rec.lang:
                        lang = rec._render_lang([res_id])[res_id]
                        template = template.with_context(lang=lang)
                        model = model.with_context(lang=lang)

                    template_ctx = {
                        'message': self.env['mail.message'].sudo().new(dict(body=values['body_html'], record_name=record.display_name)),
                        'model_description': model.display_name,
                        'company': 'company_id' in record and record['company_id'] or self.env.company,
                        'record': record,
                    }
                    body = template._render(template_ctx, engine='ir.qweb', minimal_qcontext=True)
                    values['body_html'] = self.env['mail.render.mixin']._replace_local_links(body)
            mail = self.env['mail.mail'].sudo().create(values)

            # manage attachments
            for attachment in attachments:
                attachment_data = {
                    'name': attachment[0],
                    'datas': attachment[1],
                    'type': 'binary',
                    'res_model': 'mail.message',
                    'res_id': mail.mail_message_id.id,
                }
                attachment_ids.append((4, Attachment.create(attachment_data).id))
            if attachment_ids:
                mail.write({'attachment_ids': attachment_ids})











