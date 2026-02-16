# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models, _
from odoo.addons.phone_validation.tools import phone_validation
from odoo.exceptions import UserError
from odoo.tools import html2plaintext
import json
import datetime
import requests
from odoo.exceptions import ValidationError
from odoo.http import request

REQUEST_FORM_DATA_BOUNDARY = "REQUEST_FORM_DATA_BOUNDARY"
FORM_DATA_STARTING_PAYLOAD = '--{0}\r\nContent-Disposition: form-data; name=\\"'.format(REQUEST_FORM_DATA_BOUNDARY)
FORM_DATA_MIDDLE_PAYLOAD = '\"\r\n\r\n'
FORM_DATA_ENDING_PAYLOAD = '--{0}--'.format(REQUEST_FORM_DATA_BOUNDARY)
REQUEST_CUSTOM_HEADER = {
    'content-type': "multipart/form-data; boundary={}".format(REQUEST_FORM_DATA_BOUNDARY),
    'Content-Type': "",
    'cache-control': "no-cache"
}

# class SMSDelivery(models.Model):
#     _name = 'aretx.sms.delivery'
#     # _inherit = ['mail.thread', 'mail.activity.mixin']
#     # _rec_name = 'recipient_single_number'
#     _description = 'SMS Delivery'
#     sms_sent_id = fields.Many2one('aretx.sms.composer', string='Select Vehicle', readonly=False, required=True, store=True)
#     msg_id = fields.Char(string='Msg ID', index=True, required=True, store=True,readonly=False)
#     log_date = fields.Date(string='Log Date', index=True, format="dmy", required=True, store=True,readonly=False)
#     contact = fields.Char(string='Contact', index=True, required=True, store=True,readonly=False)


# class ReminderSale(models.Model):
#     _inherit = "sale.order"
#     is_sms_reminder_sent = fields.Boolean('Is SMS Reminder Sent', default=False)
#     is_email_reminder_sent = fields.Boolean('Is Email Reminder Sent', default=False)
#     sms_reminder_text = fields.Text(string='SMS Reminder Text', index=True, tracking=True, store=True, readonly=False)
#     email_reminder_text = fields.Text(string='Email Reminder Text', index=True, tracking=True, store=True, readonly=False)


# class ReminderMove(models.Model):
#     _inherit = "account.move"
#     is_sms_reminder_sent = fields.Boolean('Is SMS Reminder Sent', default=False)
#     is_email_reminder_sent = fields.Boolean('Is Email Reminder Sent', default=False)
#     sms_reminder_text = fields.Text(string='SMS Reminder Text', index=True, tracking=True, store=True, readonly=False)
#     email_reminder_text = fields.Text(string='Email Reminder Text', index=True, tracking=True, store=True, readonly=False)


class SendSMS(models.Model):
    _name = 'aretx.sms.composer'
    # _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'recipient_single_number'
    _description = 'Send SMS Wizard'

    # documents
    res_model = fields.Char('Document Model Name')
    res_id = fields.Integer('Document ID')
    order_partner_id = fields.Selection([],store=False)#fields.Integer('Partner ID')
    # is_sale_order = fields.Boolean('Is Sale Order', default=False)
    number = fields.Char('Recipient (Number)')
    # vehicle_id = fields.Many2one('vehicle.master.model', domain="[('x_customer_id','=',res_id)]", string='Select Vehicle',required=False,store=True)
    vehicle_id = fields.Many2one('vehicle.master.model', domain="[('id','=','0')]", string='Select Vehicle',required=False,store=True)
    # vehicle_id = fields.Many2one('vehicle.master.model', related='vehicle.id', string='Select Vehicle',required=False,store=True)
    # vehicle_id = fields.Many2one('vehicle.master.model', domain="[('id','=','0')]", string='Select Vehicle',required=False,store=True)
    template_id = fields.Many2one('custom.sms.templates', string='Select Template',required=True,store=True)
    title = fields.Char(string='Title', index=True, required=False, related='template_id.name', store=True, readonly=False)
    # content = fields.Text(string='Content', index=True, required=True, tracking=True, related='template_id.description', store=True, readonly=False)
    content = fields.Text(string='Content', index=True, required=True, tracking=True, inverse='_compute_content', compute='_compute_description', store=True, readonly=False)
    recipient_single_description = fields.Text('Recipients (Partners)', compute='_compute_recipient_single',compute_sudo=False)
    recipient_single_number = fields.Char('Stored Recipient Number', compute='_compute_recipient_single',compute_sudo=False)
    recipient_single_number_itf = fields.Char(
        'Recipient Number', compute='_compute_recipient_single',
        readonly=False, compute_sudo=False, store=True,
        help='UX field allowing to edit the recipient number. If changed it will be stored onto the recipient.')
    vehicle_number = fields.Char('Vehicle Number')
    number_field_name = fields.Char('Number Field')
    balance = fields.Integer('Total SMS Balance', readonly=True)
    account_type = fields.Selection([('2', 'Transaction'), ('1', 'Promotion'), ('3', 'OPT-IN')],'Select Account Type',default='2',required="1")
    is_vehicle = fields.Boolean('Vehicle Exist', default=False)
    msg_id = fields.Char(string='Msg ID', index=True, required=False, store=True, readonly=False)
    log_date = fields.Char(string='Log Date', index=True, required=False, store=True, readonly=False)
    # 0 = sent
    #
    # 1 = Enroute(Expired)
    #
    # 2 = delivered
    #
    # 3 = Expired
    #
    # 4 = deleted
    #
    # 5 = Failed
    #
    # 8 = rejected
    #
    # 10 = fail - template
    #
    # 11 - fail - credit
    delivery_status = fields.Integer('Delivery Status', default=0,  help="0 => SENT, 1 => Enroute(Expired), 2 => delivered, 3 => Expired, 4 => deleted, 5 => Failed, 8 => rejected, 10 => fail - template, 11 => fail - credit")
    delivery_status_text = fields.Char('Delivery Status', default='SENT', compute="_compute_delivery", store=True)
    error_log_status = fields.Text('Error Log Status', index=True, required=False, store=True, readonly=False)
    error_log_text = fields.Text('Error Log Text', index=True, required=False, store=True, readonly=False)
    partner_id = fields.Many2one('res.partner', index=True, required=False, store=True, readonly=False)
    active_res_model = fields.Char('Active Document Model Name')
    active_res_id = fields.Integer('Active Document ID')

    @api.depends('delivery_status')
    @api.onchange('delivery_status')
    def _compute_delivery(self):
        switcher = {
            0: "Sent",
            1: "Enroute(Expired)",
            2: "Delivered",
            3: "Expired",
            4: "Deleted",
            5: "Failed",
            8: "Rejected",
            10: "Fail - template",
            11: "Fail - credit",
        }
        for rec in self:
            rec.delivery_status_text = switcher.get(rec.delivery_status, "Sent")

    # vehicle = fields.Many2one('vehicle.master.model', string="Select Vehicle")
    # vehicle = fields.Selection([], 'Select Vehicle')

    # template_id = fields.One2many('custom.sms.templates', 'id', string='Use Template')
    # title = fields.One2many('custom.sms.templates','template_id.name',
    #     'Title',
    #     readonly=False, store=True, required=True)
    # body = fields.One2many('custom.sms.templates','template_id.description',
    #     'Message',
    #     readonly=False, store=True, required=True)



    # @api.depends('composition_mode', 'res_model', 'res_id', 'template_id')
    # def _compute_body(self):
    #     for record in self:
    #         if record.template_id and record.composition_mode == 'comment' and record.res_id:
    #             record.body = record.template_id._render_field('body', [record.res_id], compute_lang=True)[record.res_id]
    #         elif record.template_id:
    #             record.body = record.template_id.body

    # ------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------
    # _constraints = [('_balance_check_method', 'Balance Should Be Greater Than 0.', ['balance']), ]
    _sql_constraints = [

        ('positive_balance', 'CHECK(balance > 0)', "You Don't Have Enough Balance To Send SMS.")
    ]
    # def _balance_check_method(self, kwargs):
    #     if self.balance > 0:
    #         return True
    #     else:
    #         return False

    @api.model
    def default_get(self, fields):
        result = super(SendSMS, self).default_get(fields)
        if 'res_model' in result and 'res_id' in result:
            newrecords = self._get_records(result['res_model'], result['res_id'])
            newrecords.ensure_one()
            newres = newrecords._sms_get_recipients_info(force_field=False, partner_fallback=True)
            custom_order_partner_id = []
            if newres[newrecords.id]['partner'].id:
                vehicles = []
                if result['res_model'] == 'sale.order.line':
                    if newrecords.order_id and newrecords.order_id.x_vehicle_number_id:
                        for rec in newrecords.order_id.x_vehicle_number_id:
                            vehicles.append(rec.id)
                elif 'x_vehicle_number_ids' in newres[newrecords.id]['partner'] and newres[newrecords.id]['partner'].x_vehicle_number_ids:
                    for rec in newres[newrecords.id]['partner'].x_vehicle_number_ids:
                        vehicles.append(rec.id)
                elif 'x_vehicle_number_id' in newres[newrecords.id]['partner'] and newres[newrecords.id]['partner'].x_vehicle_number_id:
                    for rec in newres[newrecords.id]['partner'].x_vehicle_number_id:
                        vehicles.append(rec.id)
                custom_order_partner_id = vehicles
        else:
            custom_order_partner_id = []
        result['order_partner_id'] = custom_order_partner_id

        return result

    # @api.onchange('vehicle_id')
    # def _onchange_vehicle_id(self):
    #     return {'domain': {'x_customer_id': [('res_partner_id', '=', 17)]}}
    #     for composer in self:
    #         records = composer._get_records()
    #         records.ensure_one()
    #         # composer.vehicle_id = None#records.x_vehicle_number_ids[0]
    #         return {'domain': {'x_customer_id': [('x_customer_id', '=', records.order_partner_id)]}}
    #         # composer.vehicle_id = fields.Many2one('vehicle.master.model', domain="[('x_customer_id','=',res_id)]", string='Select Vehicle',required=False,store=True)

    def _generate_form_data_payload(self, kwargs):
        payload = ''
        for key, value in kwargs.items():
            payload += '{0}{1}{2}{3}\r\n'.format(FORM_DATA_STARTING_PAYLOAD, key, FORM_DATA_MIDDLE_PAYLOAD, value)
        payload += FORM_DATA_ENDING_PAYLOAD
        return payload

    def _action_fetch_balance(self,account_type=None):
        #get sms settings
        query = self.env['custom.sms.setting'].browse(1)
        query.ensure_one()
        balance = 0
        if query:
            data = {}
            data[query.userid_map] = query.userid
            data[query.userid_password_map] = query.userpassword
            data[query.account_type_map] = query.account_type if account_type==None else account_type
            response = requests.get(query.balance_url, data)
            # response = requests.get(query.balance_url, headers=REQUEST_CUSTOM_HEADER, data=request_data)
            error = ["Authentication Fail","Invalid Sender ID",'Error :- Object reference not set to an instance of an object.',"No Data Found"]
            if response.status_code==200 and response.text not in error:
                sms_balance_explode = response.text.split('|')
                balance = sms_balance_explode[0]
            return balance

    @api.depends('template_id.description')
    def _compute_description(self):
        for rec in self:
            rec.content = rec.template_id.description

    def _compute_content(self):
        pass

    @api.onchange('template_id', 'vehicle_id')
    def _on_change_template_id(self):
        for rec in self:
            if rec.template_id is not False:
                data = rec.content
                if rec.vehicle_id is not False and rec.vehicle_id.x_vehicle_number_id is not False and rec.content is not False and '%vehicle%' in rec.content:
                    rec.vehicle_number = rec.vehicle_id.x_vehicle_number_id
                    data = data.replace("%vehicle%", rec.vehicle_id.x_vehicle_number_id)

                elif rec.vehicle_id is not False and rec.vehicle_id.x_vehicle_number_id is not False and rec.content is not False and rec.vehicle_number is not False and rec.vehicle_id.x_vehicle_number_id != rec.vehicle_number and rec.vehicle_number in rec.content:
                    data = data.replace(rec.vehicle_number, rec.vehicle_id.x_vehicle_number_id)
                    rec.vehicle_number = rec.vehicle_id.x_vehicle_number_id


                elif rec.vehicle_id.x_vehicle_number_id is False and rec.content is not False and rec.vehicle_number is not False and rec.vehicle_number in rec.content:
                    data = data.replace(rec.vehicle_number, "%vehicle%")
                    rec.vehicle_number = False

                if rec.content is not False and '%customer%' in rec.content:
                    records = rec._get_records()
                    records.ensure_one()
                    if records is not False and records.name is not False:
                       data = data.replace("%customer%", records.name)

                if rec.active_res_model is not False and rec.active_res_id is not False and rec.content is not False and '%bill_amount%' in rec.content and rec.active_res_model == 'account.move':
                    invoice_records = rec._get_records(active_res_model=rec.active_res_model, active_res_id=rec.active_res_id)
                    invoice_records.ensure_one()
                    if invoice_records is not False and 'amount_total' in invoice_records.fields_get():
                        data = data.replace("%bill_amount%", str(invoice_records.amount_total))
                elif rec.content is not False and '%bill_amount%' in rec.content:
                    bill_records = rec._get_records()
                    bill_records.ensure_one()
                    if bill_records is not False and 'amount_total' in bill_records.fields_get():
                        data = data.replace("%bill_amount%", str(bill_records.amount_total))

                if data:
                    rec.content = data

    @api.onchange('account_type')
    def _on_change_account_type(self):
        if self.account_type is not False:
            for composer in self:
                composer.balance = composer._action_fetch_balance(self.account_type)
                if composer.balance == 0 or composer.balance < 0:
                    raise ValidationError(_("You Don't Have Enough Balance To Send SMS."))
                    return False

    def update_content(self):
        # for rec in self:
        rec = self
        if rec.template_id is not False:
            data = rec.content
            if rec.vehicle_id is not False and rec.vehicle_id.x_vehicle_number_id is not False and rec.content is not False and '%vehicle%' in rec.content:
                rec.vehicle_number = rec.vehicle_id.x_vehicle_number_id
                data = data.replace("%vehicle%", rec.vehicle_id.x_vehicle_number_id)

            elif rec.vehicle_id is not False and rec.vehicle_id.x_vehicle_number_id is not False and rec.content is not False and rec.vehicle_number is not False and rec.vehicle_id.x_vehicle_number_id != rec.vehicle_number and rec.vehicle_number in rec.content:
                data = data.replace(rec.vehicle_number, rec.vehicle_id.x_vehicle_number_id)
                rec.vehicle_number = rec.vehicle_id.x_vehicle_number_id


            elif rec.vehicle_id.x_vehicle_number_id is False and rec.content is not False and rec.vehicle_number is not False and rec.vehicle_number in rec.content:
                data = data.replace(rec.vehicle_number, "%vehicle%")
                rec.vehicle_number = False

            if rec.content is not False and '%customer%' in rec.content:
                records = rec._get_records()
                records.ensure_one()
                if records is not False and records.name is not False:
                    data = data.replace("%customer%", records.name)

            if rec.active_res_model is not False and rec.active_res_id is not False and rec.content is not False and '%bill_amount%' in rec.content and rec.active_res_model == 'account.move':
                invoice_records = rec._get_records(active_res_model=rec.active_res_model, active_res_id=rec.active_res_id)
                invoice_records.ensure_one()
                if invoice_records is not False and 'amount_total' in invoice_records.fields_get():
                    data = data.replace("%bill_amount%", str(invoice_records.amount_total))
            elif rec.content is not False and '%bill_amount%' in rec.content:
                bill_records = rec._get_records()
                bill_records.ensure_one()
                if bill_records is not False and 'amount_total' in bill_records.fields_get():
                    data = data.replace("%bill_amount%", str(bill_records.amount_total))

            if data:
                rec.update({'content':data})
                # return data
                # rec.content = data
        return False


    @api.model
    def create(self, vals_list):
        res = super(SendSMS, self).create(vals_list)
        res.update_content()
        return res

    def open_rec(self):
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'views': False,  # view id and type
            # 'view_id': 'aretx_sms_composer_list_form',  # view id
            'view_id': self.env.ref('aos_sms_aretx.aretx_sms_composer_list_form').id,
            'res_model': 'aretx.sms.composer',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'flags': {'form': {'action_buttons': False, 'create': False, 'edit': False}}
        }

    def action_send_sms(self,):
        print('self')
        print(self)
        # print(vals_list)
        print('self')
        # get sms settings
        query = self.env['custom.sms.setting'].browse(1)
        query.ensure_one()
        if query:
            data = {}
            data[query.userid_map] = query.userid
            data[query.userid_password_map] = query.userpassword
            data[query.account_type_map] = self.account_type
            data[query.phonenumber_map] = self.recipient_single_number_itf
            data[query.msg_map] = self.content
            data[query.gsm_map] = query.gsm_sendername


            # number = self.recipient_single_number_itf;
            # text = self.content;
            # # // URL: http: // sms.infisms.co. in / API / SendSMS.aspx?UserID = XXXXXX & UserPassword = XXXXX & PhoneNumber = XXXXX & Text = TestMessaeg & SenderId = XXXXXX & AccountType = X & MessageType = X
            # $data = array(
            # $query[0]->userid = > $query[0]->sms_user_id,
            # $query[0]->userpass = > $query[0]->sms_password,
            # $query[0]->phone_number = > $number,
            # $query[0]->text = > $text,
            # $query[0]->gsm = > $query[0]->sms_gsm,
            #                               'AccountType' = > $this->input->post('account_type', TRUE),
            # );
            print(data)
            response = requests.get(query.send_url, data)
            # response = requests.get(query.balance_url, headers=REQUEST_CUSTOM_HEADER, data=request_data)
            error = ["Invalid Template","Authentication Fail", "Invalid Sender ID",
                     'Error :- Object reference not set to an instance of an object.', "No Data Found"]
            if response.status_code == 200 and response.text not in error:
                #save msg_id in sms_delivery_report table
                vals_list = {}
                vals_list['msg_id'] = response.text
                vals_list['log_date'] = datetime.datetime.now().strftime("%d%M%Y")
                vals_list['delivery_status'] = 0#datetime.datetime.now().strftime("%d%m%y")

                #status
                # 0 = sent
                #
                # 1 = Enroute(Expired)
                #
                # 2 = delivered
                #
                # 3 = Expired
                #
                # 4 = deleted
                #
                # 5 = Failed
                #
                # 8 = rejected
                #
                # 10 = fail - template
                #
                # 11 - fail - credit

                # vals_list['sms_sent_id'] = self.id
                # vals_list['contact'] = self.recipient_single_number_itf
                # res = self.env['aretx.sms.delivery'].create(vals_list)
                res = False
                for sms in self:
                    res = super(SendSMS, sms).write(vals_list)
                if res:
                    return True
                else:
                    return False
                # return res
            else:
                for sms in self:
                    res = super(SendSMS, sms).write({'error_log_status': response.status_code, 'error_log_text': response.text})
                # aretx_sms_composer.write({'error_log_status': response.status_code, 'error_log_text': response.text})
                return False
        else:
            return False

    # def action_send_sms(self):
    #     pass

    @api.depends('res_model', 'number_field_name')
    def _compute_recipient_single(self):
        for composer in self:
            records = composer._get_records()
            # if not records or not issubclass(type(records),
            #                                  self.pool['mail.thread']) or not composer.comment_single_recipient:
            #     composer.recipient_single_description = False
            #     composer.recipient_single_number = ''
            #     composer.recipient_single_number_itf = ''
            #     continue
            records.ensure_one()
            res = records._sms_get_recipients_info(force_field=composer.number_field_name, partner_fallback=True)
            vehicles = []
            #composer.balance = self._action_fetch_balance()
            # ('2', 'Transaction')
            if 'x_vehicle_number_ids' in records and records.x_vehicle_number_ids:
                # print(res[records.id]['partner'].x_vehicle_number_ids)
                for rec in records.x_vehicle_number_ids:
                    vehicles.append((rec.id, rec.x_vehicle_number_id))
            elif 'x_vehicle_number_id' in records and records.x_vehicle_number_id:
                # print(res[records.id]['partner'].x_vehicle_number_id)
                for rec in records.x_vehicle_number_id:
                    vehicles.append((rec.id, rec.x_vehicle_number_id))
            if len(vehicles) > 0:
                # composer.vehicle_id = self.env['vehicle.master.model'].search([('x_customer_id', '=', 17)])
                composer.is_vehicle = True
            # if 'order_partner_id' in records:
            #     composer.recipient_single_description = records.order_partner_id.name
            # else:
            composer.recipient_single_description = res[records.id]['partner'].name or records.display_name
            composer.partner_id = res[records.id]['partner'].id

            # composer.recipient_single_description = records.name#res[records.id]['partner'].name or records.display_name
            composer.recipient_single_number = res[records.id]['number'] or ''
            if not composer.recipient_single_number_itf:
                composer.recipient_single_number_itf = res[records.id]['number'] or ''
            if not composer.number_field_name:
                composer.number_field_name = res[records.id]['field_store']

    def _get_records(self, param_res_model=None, param_res_id=None, active_res_model=None, active_res_id=None):
        if not self.res_model and param_res_model is None and param_res_id is None and active_res_model is None and active_res_id is None or not self.res_id and param_res_model is None and param_res_id is None and active_res_model is None and active_res_id is None:
            return None
        # if self.use_active_domain:
        #     active_domain = literal_eval(self.active_domain or '[]')
        #     records = self.env[self.res_model].search(active_domain)
        # elif self.res_ids:
        #     records = self.env[self.res_model].browse(literal_eval(self.res_ids))
        # elif self.res_id:
        #     records = self.env[self.res_model].browse(self.res_id)
        # else:
        # print(self)
        # print(self.res_model)
        # records = self.env[self.res_model]
        if param_res_model is not None and param_res_id is not None:
            records = self.env[param_res_model].browse(param_res_id)
        elif active_res_model is not None and active_res_id is not None:
            records = self.env[active_res_model].browse(active_res_id)
        else:
            records = self.env[self.res_model].browse(self.res_id)
        # print(records);
        records = records.with_context(mail_notify_author=True)
        return records

    def get_current_company_value(self):

        cookies_cids = [int(r) for r in request.httprequest.cookies.get('cids').split(",")] \
            if request.httprequest.cookies.get('cids') \
            else [request.env.user.company_id.id]

        for company_id in cookies_cids:
            if company_id not in self.env.user.company_ids.ids:
                cookies_cids.remove(company_id)
        if not cookies_cids:
            cookies_cids = [self.env.company.id]
        if len(cookies_cids) == 1:
            cookies_cids.append(0)
        return cookies_cids

    def _delivery_status_check(self):
        non_delivered_status = self.env['aretx.sms.composer'].search([('msg_id', '!=', False), ('delivery_status', '=', 0)])
        print('non_delivered_status',non_delivered_status)
        query = self.env['custom.sms.setting'].browse(1)
        query.ensure_one()
        if query:
            data = {}
            data[query.userid_map] = query.userid
            data[query.userid_password_map] = query.userpassword
            for non_delivered in non_delivered_status:
                data[query.log_date_map] = non_delivered.log_date
                data[query.sent_msg_id_map] = non_delivered.msg_id
                response = requests.get(query.deliver_url, data)
                # response = requests.get(query.balance_url, headers=REQUEST_CUSTOM_HEADER, data=request_data)
                error = ["Invalid Template", "Authentication Fail", "Invalid Sender ID",
                         'Error :- Object reference not set to an instance of an object.', "No Data Found"]
                if response.status_code == 200 and response.text not in error:
                    code = response.text.split('|')[0]
                    non_delivered.write({'delivery_status': code})

        return True

    def _automatic_reminder(self, account_type=2):
        # first of all get all sale_items with state confirmed that have detailed_type = 'service' and from_order_date_number_of_days > 0 - group_by customer,service and current_date = converted(from_order_date_number_of_days)
        # company_id = str(self.get_current_company_value())
        self._cr.execute(('''select sale_order.id as sale_order_id,sale_order.x_vehicle_number_id as vehicle_id,res_partner.id as customer_id, product_template.id AS product_tmpl_id, date(sale_order.date_order), res_partner.name as customer_name, res_partner.phone, product_template.default_sms_template,CASE WHEN product_template.reminder_day_month_year='days' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' day')::interval WHEN product_template.reminder_day_month_year='month' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' month')::interval WHEN product_template.reminder_day_month_year='year' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' year')::interval END AS calculated_date_order from sale_order INNER JOIN sale_order_line ON sale_order_line.order_id = sale_order.id INNER JOIN product_product ON sale_order_line.product_id = product_product.id INNER JOIN product_template ON product_product.product_tmpl_id = product_template.id INNER JOIN res_partner ON sale_order_line.order_partner_id = res_partner.id where sale_order.state = 'sale' AND date(sale_order.date_order) = CASE WHEN product_template.reminder_day_month_year='days' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' day')::interval WHEN product_template.reminder_day_month_year='month' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' month')::interval WHEN product_template.reminder_day_month_year='year' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' year')::interval END AND product_template.detailed_type = 'service' AND res_partner.phone is not null AND product_template.default_sms_template is not null AND COALESCE(sale_order.is_sms_reminder_sent,'false') <> 'true' group by sale_order.id,res_partner.id,product_template.id,res_partner.phone,date(sale_order.date_order),sale_order.x_vehicle_number_id order by date(sale_order.date_order) DESC'''))
        record_invoice = self._cr.dictfetchall()
        print('record_invoice')
        print(record_invoice)
        print('record_invoice')
        return False
        for out_sum in record_invoice:
            sale_order_id = out_sum['sale_order_id']
            customer_id = out_sum['customer_id']
            phone = out_sum['phone']
            default_sms_template = out_sum['default_sms_template']
            sale_order = self.env['sale.order'].browse(sale_order_id)
            template_id = self.env['custom.sms.templates'].browse(default_sms_template)
            customer = self.env['res.partner'].browse(customer_id)
            vehicle_id = self.env['vehicle.master.model'].browse(out_sum['vehicle_id'])


            c_data = template_id.description
            if vehicle_id is not False and vehicle_id.x_vehicle_number_id is not False and c_data is not False and '%vehicle%' in c_data:
                c_data = c_data.replace("%vehicle%", vehicle_id.x_vehicle_number_id)


            if c_data is not False and '%customer%' in c_data:
                c_data = c_data.replace("%customer%", customer.name)

            if c_data is not False and '%bill_amount%' in c_data:
                c_data = c_data.replace("%bill_amount%", str(sale_order.amount_total))

            # create entry in aretx_sms_composer
            if vehicle_id:
                aretx_sms_composer = self.env['aretx.sms.composer'].create({
                    'res_model': 'sale.order',  # self.partner_id.id,
                    'res_id': sale_order_id,  # self.partner_id.id,
                    'number': phone,
                    'number_field_name': 'phone',
                    'partner_id': customer_id,
                    'vehicle_id': vehicle_id.id,
                    'template_id': template_id.id,
                    'title': template_id.name,
                    'content': c_data,
                    'recipient_single_number_itf': phone,
                    'vehicle_number': vehicle_id.x_vehicle_number_id,
                    'is_vehicle': 1,
                })
            else:
                aretx_sms_composer = self.env['aretx.sms.composer'].create({
                    'res_model': 'sale.order',  # self.partner_id.id,
                    'res_id': sale_order_id,  # self.partner_id.id,
                    'number': phone,
                    'number_field_name': 'phone',
                    'partner_id': customer_id,
                    'template_id': template_id.id,
                    'title': template_id.name,
                    'content': c_data,
                    'recipient_single_number_itf': phone,
                })



            # get sms settings
            query = self.env['custom.sms.setting'].browse(1)
            query.ensure_one()
            if query:
                data = {}
                data[query.userid_map] = query.userid
                data[query.userid_password_map] = query.userpassword
                data[query.account_type_map] = account_type
                data[query.phonenumber_map] = phone
                data[query.msg_map] = c_data
                data[query.gsm_map] = query.gsm_sendername

                response = requests.get(query.send_url, data)
                # response = requests.get(query.balance_url, headers=REQUEST_CUSTOM_HEADER, data=request_data)
                error = ["Invalid Template", "Authentication Fail", "Invalid Sender ID",
                         'Error :- Object reference not set to an instance of an object.', "No Data Found"]
                if response.status_code == 200 and response.text not in error:
                    # save msg_id in sms_delivery_report table
                    vals_list = {}
                    vals_list['msg_id'] = response.text
                    vals_list['log_date'] = datetime.datetime.now().strftime("%d%M%Y")
                    vals_list['delivery_status'] = 0  # datetime.datetime.now().strftime("%d%m%y")
                    sale_order.write({'is_sms_reminder_sent': 1, 'sms_reminder_text': c_data})
                    # status
                    # 0 = sent
                    #
                    # 1 = Enroute(Expired)
                    #
                    # 2 = delivered
                    #
                    # 3 = Expired
                    #
                    # 4 = deleted
                    #
                    # 5 = Failed
                    #
                    # 8 = rejected
                    #
                    # 10 = fail - template
                    #
                    # 11 - fail - credit

                    aretx_sms_composer.write(vals_list)
                    # return True
                else:
                    aretx_sms_composer.write({'error_log_status': response.status_code, 'error_log_text': response.text})
                    # return True
            else:
                return True


        #Email-Automation
        self._cr.execute(('''select sale_order.id as sale_order_id,res_partner.id as customer_id, product_template.id AS product_tmpl_id, date(sale_order.date_order), res_partner.name as customer_name, res_partner.email, product_template.default_email_template,CASE WHEN product_template.reminder_day_month_year='days' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' day')::interval WHEN product_template.reminder_day_month_year='month' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' month')::interval WHEN product_template.reminder_day_month_year='year' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' year')::interval END AS calculated_date_order from sale_order INNER JOIN sale_order_line ON sale_order_line.order_id = sale_order.id INNER JOIN product_product ON sale_order_line.product_id = product_product.id INNER JOIN product_template ON product_product.product_tmpl_id = product_template.id INNER JOIN res_partner ON sale_order_line.order_partner_id = res_partner.id where sale_order.state = 'sale' AND date(sale_order.date_order) = CASE WHEN product_template.reminder_day_month_year='days' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' day')::interval WHEN product_template.reminder_day_month_year='month' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' month')::interval WHEN product_template.reminder_day_month_year='year' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' year')::interval END AND product_template.detailed_type = 'service' AND res_partner.email is not null AND product_template.default_email_template is not null AND COALESCE(sale_order.is_email_reminder_sent,'false') <> 'true' group by sale_order.id,res_partner.id,product_template.id,res_partner.email,date(sale_order.date_order) order by date(sale_order.date_order) DESC'''))
        email_record_invoice = self._cr.dictfetchall()

        for email in email_record_invoice:
            sale_order_id = email['sale_order_id']
            email_address = email['email']
            sale_order = self.env['sale.order'].browse(sale_order_id)
            template_id = email['default_email_template']
            lang = self.env.context.get('lang')
            template = self.env['mail.template'].browse(template_id)
            template.add_to_queue_mail(sale_order_id, force_send=False)
            sale_order.write({'is_email_reminder_sent': 1})

    # def _automatic_reminder_invoice(self, account_type=2):
    #     # first of all get all sale_items with state confirmed that have detailed_type = 'service' and from_order_date_number_of_days > 0 - group_by customer,service and current_date = converted(from_order_date_number_of_days)
    #     # company_id = str(self.get_current_company_value())
    #     self._cr.execute(('''select account_move.id as account_move_id,account_move.vehicle_number as vehicle_id,res_partner.id as customer_id, product_template.id AS product_tmpl_id, date(account_move.invoice_date), res_partner.name as customer_name, res_partner.phone, product_template.default_sms_template,CASE WHEN product_template.reminder_day_month_year='days' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' day')::interval WHEN product_template.reminder_day_month_year='month' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' month')::interval WHEN product_template.reminder_day_month_year='year' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' year')::interval END AS calculated_invoice_date from account_move INNER JOIN account_move_line ON account_move_line.move_id = account_move.id INNER JOIN product_product ON account_move_line.product_id = product_product.id INNER JOIN product_template ON product_product.product_tmpl_id = product_template.id INNER JOIN res_partner ON account_move_line.partner_id = res_partner.id where account_move.move_type = 'out_invoice' AND account_move.state = 'posted' AND date(account_move.invoice_date) = CASE WHEN product_template.reminder_day_month_year='days' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' day')::interval WHEN product_template.reminder_day_month_year='month' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' month')::interval WHEN product_template.reminder_day_month_year='year' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' year')::interval END AND product_template.detailed_type = 'service' AND res_partner.phone is not null AND product_template.default_sms_template is not null AND COALESCE(account_move.is_sms_reminder_sent,'false') <> 'true' group by account_move.id,res_partner.id,product_template.id,res_partner.phone,date(account_move.invoice_date),account_move.vehicle_number order by date(account_move.invoice_date) DESC'''))
    #     record_invoice = self._cr.dictfetchall()
    #     print('record_invoice')
    #     print(record_invoice)
    #     print('record_invoice')
    #
    #     for out_sum in record_invoice:
    #         account_move_id = out_sum['account_move_id']
    #         customer_id = out_sum['customer_id']
    #         phone = out_sum['phone']
    #         default_sms_template = out_sum['default_sms_template']
    #         account_move = self.env['account.move'].browse(account_move_id)
    #         template_id = self.env['custom.sms.templates'].browse(default_sms_template)
    #         customer = self.env['res.partner'].browse(customer_id)
    #         vehicle_id = self.env['vehicle.master.model'].browse(out_sum['vehicle_id'])
    #
    #
    #         c_data = template_id.description
    #         if vehicle_id is not False and vehicle_id.x_vehicle_number_id is not False and c_data is not False and '%vehicle%' in c_data:
    #             c_data = c_data.replace("%vehicle%", vehicle_id.x_vehicle_number_id)
    #
    #
    #         if c_data is not False and '%customer%' in c_data:
    #             c_data = c_data.replace("%customer%", customer.name)
    #
    #         if c_data is not False and '%bill_amount%' in c_data:
    #             c_data = c_data.replace("%bill_amount%", str(account_move.amount_total))
    #
    #         # create entry in aretx_sms_composer
    #         if vehicle_id:
    #             aretx_sms_composer = self.env['aretx.sms.composer'].create({
    #                 'res_model': 'account.move',  # self.partner_id.id,
    #                 'res_id': account_move_id,  # self.partner_id.id,
    #                 'number': phone,
    #                 'number_field_name': 'phone',
    #                 'partner_id': customer_id,
    #                 'vehicle_id': vehicle_id.id,
    #                 'template_id': template_id.id,
    #                 'title': template_id.name,
    #                 'content': c_data,
    #                 'recipient_single_number_itf': phone,
    #                 'vehicle_number': vehicle_id.x_vehicle_number_id,
    #                 'is_vehicle': 1,
    #             })
    #         else:
    #             aretx_sms_composer = self.env['aretx.sms.composer'].create({
    #                 'res_model': 'account.move',  # self.partner_id.id,
    #                 'res_id': account_move_id,  # self.partner_id.id,
    #                 'number': phone,
    #                 'number_field_name': 'phone',
    #                 'partner_id': customer_id,
    #                 'template_id': template_id.id,
    #                 'title': template_id.name,
    #                 'content': c_data,
    #                 'recipient_single_number_itf': phone,
    #             })
    #
    #
    #
    #         # get sms settings
    #         query = self.env['custom.sms.setting'].browse(1)
    #         query.ensure_one()
    #         if query:
    #             data = {}
    #             data[query.userid_map] = query.userid
    #             data[query.userid_password_map] = query.userpassword
    #             data[query.account_type_map] = account_type
    #             data[query.phonenumber_map] = phone
    #             data[query.msg_map] = c_data
    #             data[query.gsm_map] = query.gsm_sendername
    #
    #             response = requests.get(query.send_url, data)
    #             # response = requests.get(query.balance_url, headers=REQUEST_CUSTOM_HEADER, data=request_data)
    #             error = ["Invalid Template", "Authentication Fail", "Invalid Sender ID",
    #                      'Error :- Object reference not set to an instance of an object.', "No Data Found"]
    #             if response.status_code == 200 and response.text not in error:
    #                 # save msg_id in sms_delivery_report table
    #                 vals_list = {}
    #                 vals_list['msg_id'] = response.text
    #                 vals_list['log_date'] = datetime.datetime.now().strftime("%d%M%Y")
    #                 vals_list['delivery_status'] = 0  # datetime.datetime.now().strftime("%d%m%y")
    #                 account_move.write({'is_sms_reminder_sent': 1, 'sms_reminder_text': c_data})
    #                 # status
    #                 # 0 = sent
    #                 #
    #                 # 1 = Enroute(Expired)
    #                 #
    #                 # 2 = delivered
    #                 #
    #                 # 3 = Expired
    #                 #
    #                 # 4 = deleted
    #                 #
    #                 # 5 = Failed
    #                 #
    #                 # 8 = rejected
    #                 #
    #                 # 10 = fail - template
    #                 #
    #                 # 11 - fail - credit
    #
    #                 aretx_sms_composer.write(vals_list)
    #                 # return True
    #             else:
    #                 aretx_sms_composer.write({'error_log_status': response.status_code, 'error_log_text': response.text})
    #                 # return True
    #         else:
    #             return True
    #
    #
    #     #Email-Automation
    #     self._cr.execute(('''select account_move.id as account_move_id,res_partner.id as customer_id, product_template.id AS product_tmpl_id, date(account_move.invoice_date), res_partner.name as customer_name, res_partner.email, product_template.default_email_template,CASE WHEN product_template.reminder_day_month_year='days' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' day')::interval WHEN product_template.reminder_day_month_year='month' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' month')::interval WHEN product_template.reminder_day_month_year='year' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' year')::interval END AS calculated_invoice_date from account_move INNER JOIN account_move_line ON account_move_line.move_id = account_move.id INNER JOIN product_product ON account_move_line.product_id = product_product.id INNER JOIN product_template ON product_product.product_tmpl_id = product_template.id INNER JOIN res_partner ON account_move_line.partner_id = res_partner.id where account_move.state = 'sale' AND date(account_move.invoice_date) = CASE WHEN product_template.reminder_day_month_year='days' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' day')::interval WHEN product_template.reminder_day_month_year='month' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' month')::interval WHEN product_template.reminder_day_month_year='year' THEN DATE(NOW()) - concat(product_template.from_order_date_number_of_days,' year')::interval END AND product_template.detailed_type = 'service' AND res_partner.email is not null AND product_template.default_email_template is not null AND COALESCE(account_move.is_email_reminder_sent,'false') <> 'true' group by account_move.id,res_partner.id,product_template.id,res_partner.email,date(account_move.invoice_date) order by date(account_move.invoice_date) DESC'''))
    #     email_record_invoice = self._cr.dictfetchall()
    #
    #     for email in email_record_invoice:
    #         account_move_id = email['account_move_id']
    #         email_address = email['email']
    #         account_move = self.env['account.move'].browse(account_move_id)
    #         template_id = email['default_email_template']
    #         lang = self.env.context.get('lang')
    #         template = self.env['mail.template'].browse(template_id)
    #         template.add_to_queue_mail(account_move_id, force_send=False)
    #         account_move.write({'is_email_reminder_sent': 1})



