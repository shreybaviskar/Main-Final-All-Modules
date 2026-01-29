from odoo import models, api, fields
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import requests
import datetime
from odoo.http import request
from odoo import api, fields, models, _, tools
from datetime import date, timedelta
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
import logging
from datetime import date
import base64

_logger = logging.getLogger(__name__)


class TyreServiceReminder(models.Model):
    _name = 'tyre.service.reminder'
    _description = 'Tyre Service Reminder Cron'

    @api.model
    def _cron_tyre_service_reminder1(self, account_type=2):
        message = "hi test from Odoo via Green API"

        GREEN_API_URL = "https://api.green-api.com/waInstance7107346943/sendMessage/814baecb2a9447248923cd769ed527bfd1664438ce864ee49f"

        payload = {
            "chatId": "917405292322@c.us",  # 👈 your number in proper format
            "message": message
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(GREEN_API_URL, json=payload, headers=headers)

        print("response.status_code", response.status_code)
        print("response.text", response.text)

        return False

    @api.model
    def _cron_tyre_service_reminder(self, account_type=2):
        """Send reminder messages per vehicle based on configuration."""
        ir_config = self.env['ir.config_parameter'].sudo()
        km_limit = int(ir_config.get_param('tyreshop.tyre_message_km', default=5000))
        month_limit = int(ir_config.get_param('tyreshop.tyre_message_months', default=3))

        print('system settings')
        print(km_limit, month_limit)

        today = fields.Date.today()
        Vehicle = self.env['vehicle.master.model'].sudo()
        print('today date', today)
        print('Vehicle', Vehicle)

        vehicles = Vehicle.search([('x_avg_km', '>', 0)])
        print('vehicles', vehicles)
        template_id = self.env['custom.sms.templates'].browse(1)

        for vehicle in vehicles:
            # Get last date properly
            c_data = template_id.description
            print('c_data', c_data)
            last_date = vehicle.last_message_date
            # print('last_date', last_date)
            if not last_date and vehicle.create_date:
                # Convert datetime to date
                last_date = vehicle.create_date.date()
            elif not last_date:
                last_date = today
            print('last_date', last_date)
            days_since_last = (today - last_date).days
            print('days_since_last', days_since_last)
            months_since_last = days_since_last / 30.0
            print('months_since_last', months_since_last)
            monthly_avg = vehicle.x_avg_km  # Assuming this is "average km per month"
            print('monthly_avg', monthly_avg)
            expected_km = monthly_avg * months_since_last
            print('expected_km', expected_km)
            # Safe subtraction (both are datetime.date)
            days_diff = (today - last_date).days
            print('days_diff', days_diff)
            month_days = month_limit * 30
            print('month_days', month_days)
            km_due = vehicle.x_avg_km >= km_limit
            print('expected_km')
            print(expected_km)
            print('km_limit')
            print(km_limit)
            km_due = expected_km >= km_limit
            print('km_due')
            print(km_due)
            month_due = days_diff >= month_days
            month_due = months_since_last >= month_limit
            print('month_due')
            print(month_due)
            partner = vehicle.x_customer_id
            print(partner.mobile)
            if not partner.mobile:
                raise ValidationError("Please update the mobile number before proceeding!")

            if km_due or month_due and partner.mobile:
                partner = vehicle.x_customer_id
                print('started a sending a msg to partner !!!!')
                print(vehicle.x_customer_id)
                print(partner)
                print(vehicle)
                x_avg_km = vehicle.x_avg_km
                message = (
                    f"Dear {partner.name}, Mobile Number {partner.mobile}, your vehicle ({vehicle.x_vehicle_number_id or partner_id.name}) "
                    f"has run {vehicle.x_avg_km} KM. It's time for a tyre service check!"
                )
                print('x_avg_km', x_avg_km)

                # Post message to chatter
                if c_data is not False and partner and '%partner_name%' in c_data:
                    c_data = c_data.replace("%partner_name%", partner.name)

                if c_data is not False and '%vehicle_x_vehicle_number_id%' in c_data:
                    c_data = c_data.replace("%vehicle_x_vehicle_number_id%", vehicle.x_vehicle_number_id)
                print('c_data', c_data)
                if c_data is not False and '%vehicle_x_avg_km%' in c_data:
                    c_data = c_data.replace("%vehicle_x_avg_km%", str(x_avg_km))
                print('c_data', c_data)

                partner.message_post(body=message)
                # Reset values
                vehicle.last_message_date = today
                # create entry in aretx_sms_composer
                if vehicle:
                    aretx_sms_composer = self.env['aretx.sms.composer'].create({
                        'res_model': 'vehicle.master.model',  # self.partner_id.id,
                        'res_id': vehicle.id,  # self.partner_id.id,
                        'number': partner.mobile,
                        'number_field_name': 'phone',
                        'partner_id': partner.id,
                        'vehicle_id': vehicle.id,
                        'template_id': template_id.id,
                        'title': template_id.name,
                        'content': c_data,
                        'recipient_single_number_itf': partner.mobile,
                        'vehicle_number': vehicle.x_vehicle_number_id,
                        'is_vehicle': 1,
                    })
                else:
                    aretx_sms_composer = self.env['aretx.sms.composer'].create({
                        'res_model': 'vehicle.master.model',  # self.partner_id.id,
                        'res_id': vehicle,  # self.partner_id.id,
                        'number': partner.mobile,
                        'number_field_name': 'phone',
                        'partner_id': partner.id,
                        'template_id': template_id.id,
                        'title': template_id.name,
                        'content': c_data,
                    })
                query = self.env['custom.sms.setting'].browse(1)
                print('query', query)
                query.ensure_one()
                clean_phone = partner.mobile.replace("+91", "").strip()
                clean_phone = partner.mobile.replace("+91", "").replace(" ", "").strip()

                print(clean_phone)
                if query:
                    data = {}
                    data[query.userid_map] = query.userid
                    data[query.userid_password_map] = query.userpassword
                    data[query.account_type_map] = account_type
                    data[query.phonenumber_map] = clean_phone
                    data[query.msg_map] = c_data
                    data[query.gsm_map] = query.gsm_sendername
                    print('data', data)

                    response = requests.get(query.send_url, data)
                    print('sms sent to partner.')
                    print('response', response)
                    # response = requests.get(query.balance_url, headers=REQUEST_CUSTOM_HEADER, data=request_data)
                    error = ["Invalid Template", "Authentication Fail", "Invalid Sender ID",
                             'Error :- Object reference not set to an instance of an object.', "No Data Found"]
                    if response.status_code == 200 and response.text not in error:
                        # save msg_id in sms_delivery_report table
                        vals_list = {}
                        vals_list['msg_id'] = response.text
                        vals_list['log_date'] = datetime.datetime.now().strftime("%d %B %Y")

                        vals_list['delivery_status'] = 0  # datetime.datetime.now().strftime("%d%m%y")
                        print('vals_list', vals_list)
                        aretx_sms_composer.write(vals_list)
                        # return True
                    else:
                        aretx_sms_composer.write(
                            {'error_log_status': response.status_code, 'error_log_text': response.text})
                        # return True

    @api.model
    def send_whatsapp_service_reminder(self, template, vehicle):
        provider = template.provider_id
        if not provider:
            raise UserError("No WhatsApp provider configured.")
        channel = provider.get_channel_whatsapp(vehicle.x_customer_id, self.env.user)
        print('channel', channel)
        # return False
        if not channel:
            raise UserError("No WhatsApp channel created.")
        # Render template
        body = template.body_html or template.body
        body = body.replace("{{1}}", str(vehicle.x_customer_id.name))
        body = body.replace("{{2}}", str(vehicle.x_vehicle_number_id))
        body = body.replace("{{3}}", str(vehicle.x_avg_km))

        print('body', body)
        print('vehicle.x_customer_id.id', vehicle.x_customer_id.id)
        msg_vals = {
            'body': tools.html2plaintext(body) if body else '',
            'author_id': self.env.user.partner_id.id,
            'model': 'vehicle.master.model',
            'res_id': vehicle.id,
            'message_type': 'wa_msgs',
            'isWaMsgs': True,
            'subtype_id': self.env.ref('mail.mt_comment').id,
            'partner_ids': [(4, vehicle.x_customer_id.id)],
        }
        print('msg_vals', msg_vals)

        msg = self.env['mail.message'].sudo().create(msg_vals)
        print('msg', msg)

        if channel and msg:
            channel._notify_thread(msg, msg_vals)
        else:
            _logger.warning("Skipped sending WhatsApp message — missing channel or msg record.")

    @api.model
    def _cron_tyre_service_wa_reminder(self):
        """Send reminder messages per vehicle based on configuration."""
        ir_config = self.env['ir.config_parameter'].sudo()
        km_limit = int(ir_config.get_param('tyreshop.tyre_message_km', default=5000))
        month_limit = int(ir_config.get_param('tyreshop.tyre_message_months', default=3))
        reminder_message_payment_days = int(ir_config.get_param('tyreshop.reminder_message_payment_days', default=3))

        print('system settings')
        print(km_limit, month_limit, reminder_message_payment_days)

        today = fields.Date.today()
        Vehicle = self.env['vehicle.master.model'].sudo()
        vehicles = Vehicle.search([('x_avg_km', '>', 0)])
        template = self.env['wa.template'].search([
            ('name', '=', 'reminder_service')
        ], limit=1)

        for vehicle in vehicles:
            # Get last date properly
            # c_data = template_id.description
            last_date = vehicle.last_wa_message_date
            # print('last_date', last_date)
            if not last_date and vehicle.create_date:
                # Convert datetime to date
                last_date = vehicle.create_date.date()
            elif not last_date:
                last_date = today
            days_since_last = (today - last_date).days
            months_since_last = days_since_last / 30.0
            monthly_avg = vehicle.x_avg_km  # Assuming this is "average km per month"
            expected_km = monthly_avg * months_since_last
            # Safe subtraction (both are datetime.date)
            days_diff = (today - last_date).days
            month_days = month_limit * 30
            km_due = vehicle.x_avg_km >= km_limit
            km_due = expected_km >= km_limit
            month_due = days_diff >= month_days
            month_due = months_since_last >= month_limit
            print('month_due')
            print(month_due)
            print('km_due')
            print(km_due)
            partner = vehicle.x_customer_id
            print('partner.mobile')
            print(partner.mobile)
            if not partner.mobile:
                raise ValidationError("Please update the mobile number before proceeding!")

            if km_due or month_due and partner.mobile:
                partner = vehicle.x_customer_id
                print('started a sending a msg to partner !!!!')
                print(vehicle.x_customer_id)
                print(partner)
                print(vehicle)
                x_avg_km = vehicle.x_avg_km
                message = (
                    f"Dear {partner.name}, Mobile Number {partner.mobile}, your vehicle ({vehicle.x_vehicle_number_id or partner_id.name}) "
                    f"has run {vehicle.x_avg_km} KM. It's time for a tyre service check!"
                )
                print('x_avg_km', x_avg_km)
                # vehicle_cron = self.env['tyre.service.reminder'].browse()
                partner.message_post(body=message)
                try:

                    # self.send_whatsapp_service_reminder(template, vehicle)
                    company_id = self.env.company.id

                    print('company....', company_id)
                    provider = self.env['provider'].search([('company_id', '=', company_id)], limit=1)
                    user_partner = provider.user_id.partner_id
                    graph_api_instance_id = provider.graph_api_instance_id
                    graph_api_token = provider.graph_api_token
                    print(graph_api_instance_id)
                    print(graph_api_token)
                    PHONE_NUMBER_ID = graph_api_instance_id
                    ACCESS_TOKEN = graph_api_token

                    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

                    #
                    clean_phone = partner.mobile.replace("+91", "").replace(" ", "").strip()
                    print('clean_phone', clean_phone)
                    payload = {
                        "messaging_product": "whatsapp",
                        "to": clean_phone,
                        "type": "template",
                        "template": {
                            "name": "reminder_service",
                            "language": {"code": "en"},
                            "components": [
                                {
                                    "type": "body",
                                    "parameters": [
                                        {"type": "text", "text": partner.name},  # {{1}}
                                        {"type": "text", "text": vehicle.x_vehicle_number_id},  # {{2}}
                                        {"type": "text", "text": vehicle.x_avg_km},  # {{3}}
                                    ]
                                }
                            ]
                        }
                    }

                    headers = {
                        "Authorization": f"Bearer {ACCESS_TOKEN}",
                        "Content-Type": "application/json",
                    }
                    _logger.info("WhatsApp Message sent: %s", payload)

                    try:
                        response = requests.post(url, json=payload, headers=headers)
                        _logger.info("WhatsApp Cloud Status: %s", response.status_code)
                        _logger.info("WhatsApp Cloud Response: %s", response.text)

                        if response.status_code not in (200, 201):
                            raise Exception(f"WhatsApp API ERROR → {response.text}")

                    except Exception as e:
                        _logger.error("WhatsApp Failed: %s", str(e))

                    vehicle.write({
                        'last_wa_message_date': today,
                    })
                    current_dt = datetime.datetime.now()
                    message = (
                        f"Dear {partner.name}, Mobile Number {partner.mobile}, your vehicle ({vehicle.x_vehicle_number_id or partner_id.name}) "
                        f"has run {vehicle.x_avg_km} KM. It's time for a tyre service check!"
                    )

                    res = request.env['whatsapp.history'].sudo().create(
                        {
                            'message': message,
                            'message_id': "",
                            'author_id': user_partner.id,
                            'type': 'delivered',
                            'partner_id': partner.id,
                            'phone': partner.mobile,
                            'attachment_ids': "",
                            'provider_id': provider.id,
                            'company_id': provider.company_id.id,
                            'date': current_dt
                        })

                    print("✅ WhatsApp History Create", res)
                    print("✅ WhatsApp reminder sent for vehicle service", vehicle.id)

                except Exception as e:
                    print("❌ ERROR:", e)
                    _logger.error("WhatsApp reminder failed for vehicle service %s: %s", vehicle.id, e)


class AccountMove(models.Model):
    _inherit = 'account.move'

    last_reminder_date = fields.Date(
        string="Last SMS Reminder Date",
        default=lambda self: fields.Date.today()
    )
    last_wa_message_date = fields.Date(string="Last Whatsapp Message Date")

    reminder_count = fields.Integer(string="Reminder Count", default=0, readonly=True)

    def _generate_pdf_and_attachment(self):
        self.ensure_one()

        # STEP 1: locate correct invoice report by name
        report = self.env['ir.actions.report'].search([
            ('report_name', 'in', [
                'account.report_invoice_with_payments',
                'account.report_invoice',
            ])
        ], limit=1)

        if not report:
            _logger.error("No valid invoice report found!")
            return False

        try:
            # STEP 2: FINAL CORRECT SIGNATURE FOR YOUR ODOO 17 VERSION
            pdf_bytes, _format = report._render(
                report.report_name,  # argument 1: report_ref
                res_ids=[self.id],  # argument 2: list of IDs
                data=None  # optional
            )
        except Exception as e:
            _logger.error("PDF Render Failed: %s", e)
            return False

        # STEP 3: Create attachment
        attachment = self.env['ir.attachment'].sudo().create({
            'name': f"{self.name.replace('/', '_')}.pdf",
            'datas': base64.b64encode(pdf_bytes),
            'type': 'binary',
            'mimetype': 'application/pdf',
            'res_model': 'account.move',
            'res_id': self.id,
        })

        return attachment

    @api.model
    def _cron_send_payment_reminder(self, account_type=2):
        """Send automatic payment reminders for overdue invoices"""
        ir_config = self.env['ir.config_parameter'].sudo()
        reminder_message_payment_days = int(ir_config.get_param('tyreshop.reminder_message_payment_days', default=3))
        today = date.today()
        # print('today', today)
        overdue_invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('payment_state', '!=', 'paid'),
            ('invoice_date_due', '!=', False),
            ('invoice_date_due', '<', today),
        ])
        print('overdue_invoices', overdue_invoices)
        for invoice in overdue_invoices:
            # Avoid spamming – send only once every 3 days
            last_reminder_date = invoice.last_reminder_date or date(1999, 1, 1)
            if last_reminder_date and (today - last_reminder_date).days < reminder_message_payment_days:
                print('ran')
                continue
            print('come in')
            partner = invoice.partner_id
            print('partner', partner)
            email_to = partner.email
            print('email_to', email_to)
            if not email_to:
                continue

            # Compose email
            subject = _("Payment Reminder for Invoice %s") % (invoice.name)
            body = f"""
            <p>Dear {partner.name},</p>
            <p>This is a kind reminder that invoice <b>{invoice.name}</b> 
            with an amount of <b>{invoice.amount_total} {invoice.currency_id.name}</b> 
            was due on <b>{invoice.invoice_date_due}</b>.</p>
            <p>Please make the payment at your earliest convenience.</p>
            <p>Thank you,<br/>
            {invoice.company_id.name}</p>
            """
            body1 = "Dear %partner.name%, This is a kind reminder that invoice %invoice.name% with an amount of %inv.amount% was due on %data%.Please make the payment at your earliest convenience.Thank you"

            # Send mail
            mail_values = {
                'subject': subject,
                'body_html': body,
                'email_to': email_to,
                'email_from': invoice.company_id.email or self.env.user.email,
            }
            # print('mail_values', mail_values)
            # send Email
            # self.env['mail.mail'].create(mail_values).send()
            # create chatter acitivity
            partner.message_post(body=body)

            # Update reminder fields
            invoice.write({
                'last_reminder_date': today,
                'last_wa_message_date': today,
                'reminder_count': invoice.reminder_count + 1
            })
            print('invoice', invoice)
            template_id = self.env['custom.sms.templates'].browse(2)

            if invoice:
                aretx_sms_composer = self.env['aretx.sms.composer'].create({
                    'res_model': 'account.move',  # self.partner_id.id,
                    'log_date': datetime.datetime.now().strftime("%d%B%Y"),
                    'res_id': invoice.id,  # self.partner_id.id,
                    'number': partner.mobile,
                    'number_field_name': 'phone',
                    'partner_id': partner.id,
                    # 'vehicle_id': vehicle.id,
                    'template_id': template_id.id,
                    'title': template_id.name,
                    'content': body,
                    'recipient_single_number_itf': partner.mobile,
                    # 'vehicle_number': vehicle.x_vehicle_number_id,
                    'is_vehicle': 1,
                })
            else:
                continue
                # Send Message

            query = self.env['custom.sms.setting'].browse(1)
            c_data = template_id.description
            # Post message to chatter
            if c_data is not False and partner and '%partner.name%' in c_data:
                c_data = c_data.replace("%partner.name%", partner.name)
            if c_data is not False and '%invoice.name%' in c_data:
                c_data = c_data.replace("%invoice.name%", invoice.name)
            if c_data is not False and '%inv.amount%' in c_data:
                c_data = c_data.replace("%inv.amount%", str(invoice.amount_total))
            if c_data is not False and '%data%' in c_data:
                c_data = c_data.replace("%data%", str(invoice.invoice_date_due))

            print('c_data', c_data)

            print('query', query)
            query.ensure_one()
            clean_phone = partner.mobile.replace("+91", "").strip()
            clean_phone = partner.mobile.replace("+91", "").replace(" ", "").strip()

            print(clean_phone)
            if query:
                data = {}
                data[query.userid_map] = query.userid
                data[query.userid_password_map] = query.userpassword
                data[query.account_type_map] = account_type
                data[query.phonenumber_map] = clean_phone
                data[query.msg_map] = c_data
                data[query.gsm_map] = query.gsm_sendername
                print('data', data)

                response = requests.get(query.send_url, data)
                print('sms sent to partner.')
                print('response', response)
                print('response', response.text)
                # response = requests.get(query.balance_url, headers=REQUEST_CUSTOM_HEADER, data=request_data)
                error = ["Invalid Template", "Authentication Fail", "Invalid Sender ID",
                         'Error :- Object reference not set to an instance of an object.', "No Data Found"]
                if response.status_code == 200 and response.text not in error:
                    # save msg_id in sms_delivery_report table
                    vals_list = {}
                    vals_list['msg_id'] = response.text
                    print('datetime.datetime.now')
                    print(datetime.datetime.now().strftime("%d%m%y"))
                    print('datetime.datetime.now')
                    vals_list['log_date'] = datetime.datetime.now().strftime("%d %B %Y")
                    vals_list['delivery_status'] = 0  # datetime.datetime.now().strftime("%d%m%y")
                    # print('vals_list', vals_list)
                    aretx_sms_composer.write(vals_list)
                    # return True
                else:
                    aretx_sms_composer.write(
                        {'error_log_status': response.status_code, 'error_log_text': response.text})
                    # return True

    def send_whatsapp_payment_reminder(self, template, invoice):
        self.ensure_one()
        # print('template',template)
        # print('template.provider_id',template.provider_id)
        provider = template.provider_id
        # print('provider', provider)
        if not provider:
            raise UserError("No WhatsApp provider configured.")
        channel = provider.get_channel_whatsapp(invoice.partner_id, self.env.user)
        print('channel', channel)
        if not channel:
            raise UserError("No WhatsApp channel created.")

        # Render template
        body = template.body_html or template.body
        body = body.replace("{{1}}", invoice.partner_id.name)
        body = body.replace("{{2}}", invoice.name)
        body = body.replace("{{3}}", str(invoice.amount_residual))
        body = body.replace("{{4}}", str(invoice.invoice_date_due))
        print('body', body)
        # return False
        msg_vals = {
            'body': tools.html2plaintext(body) if body else '',
            'author_id': self.env.user.partner_id.id,
            'model': 'account.move',
            'res_id': invoice.id,
            'message_type': 'wa_msgs',
            'isWaMsgs': True,
            'subtype_id': self.env.ref('mail.mt_comment').id,
            'partner_ids': [(4, invoice.partner_id.id)],
        }
        _logger.info('msg_vals', msg_vals)
        _logger.info(msg_vals)
        print('msg_vals', msg_vals)

        msg = self.env['mail.message'].sudo().create(msg_vals)
        print('msg', msg)

        channel._notify_thread(msg, msg_vals)

    #md
    @api.model
    def _cron_send_payment_wa_reminder(self):
        ir_config = self.env['ir.config_parameter'].sudo()
        reminder_message_payment_days = int(ir_config.get_param('tyreshop.reminder_message_payment_days', default=3))
        today = date.today()
        overdue_invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', '!=', 'paid'),
            ('invoice_date_due', '<=', today),
        ])
        print('overdue_invoices.......', overdue_invoices)
        template = self.env['wa.template'].search([
            ('name', '=', 'reminder_payment')
        ], limit=1)
        for invoice in overdue_invoices:
            last_reminder_date = invoice.last_wa_message_date or date(1999, 1, 1)
            print('invoice', invoice.name)
            print('today', today)
            print('invoice.invoice_date_due', invoice.invoice_date_due)
            remain_days = (today - last_reminder_date).days
            print('remain_days', remain_days)
            print('reminder_message_payment_days', reminder_message_payment_days)
            is_due_today = today == invoice.invoice_date_due
            print('is_due_today', is_due_today)
            if last_reminder_date and (today - last_reminder_date).days < reminder_message_payment_days and (
                    is_due_today == False):
                print('if')
                print('last_reminder_date', last_reminder_date)
                print('today', today)
                print('today', today)
                continue
            print('else')
            try:
                # PDF
                # Check existing attachment
                attachment = self.env['ir.attachment'].search([
                    ('res_model', '=', 'account.move'),
                    ('res_id', '=', invoice.id),
                    ('mimetype', '=', 'application/pdf'),
                ], limit=1)

                if not attachment:
                    # Generate PDF
                    pdf_content = self.env.ref("account.report_invoice_with_payments")._render_qweb_pdf(invoice.id)[0]
                    pdf_base64 = base64.b64encode(pdf_content)

                    # Create PUBLIC attachment
                    attachment = self.env['ir.attachment'].sudo().create({
                        'name': f"{invoice.name}.pdf",
                        'type': 'binary',
                        'datas': pdf_base64,
                        'mimetype': 'application/pdf',
                        'public': True,
                    })
                # Always generate public token
                attachment.generate_access_token()

                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                pdf_url = f"{base_url}/web/content/{attachment.id}"
                _logger.info(base_url)
                _logger.info(pdf_url)

                # PDF
                print('started base_url', base_url)
                print('started pdf_url', pdf_url)
                print('started invoice', invoice)
                provider = self.env['provider'].search([('company_id', '=', invoice.company_id.id)], limit=1)
                graph_api_instance_id = provider.graph_api_instance_id
                user_partner = provider.user_id.partner_id
                graph_api_token = provider.graph_api_token
                print(graph_api_instance_id)
                print(graph_api_token)
                PHONE_NUMBER_ID = graph_api_instance_id
                ACCESS_TOKEN = graph_api_token

                url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

                #
                clean_phone = invoice.partner_id.mobile.replace("+91", "").replace(" ", "").strip()
                print('clean_phone', clean_phone)
                payload = {
                    "messaging_product": "whatsapp",
                    "to": clean_phone,
                    "type": "template",
                    "template": {
                        "name": "payment_overdue",
                        "language": {"code": "en"},
                        "components": [
                            {
                                "type": "header",
                                "parameters": [
                                    {
                                        "type": "document",
                                        "document": {
                                            "link": pdf_url,
                                            "filename": invoice.name
                                        }
                                    }
                                ]
                            },
                            {
                                "type": "body",
                                "parameters": [
                                    {"type": "text", "text": invoice.partner_id.name},  # {{1}}
                                    {"type": "text", "text": invoice.name},  # {{2}}
                                    {"type": "text", "text": str(invoice.amount_residual)},  # {{3}}
                                    {"type": "text", "text": invoice.invoice_date_due.strftime('%Y-%m-%d')},  # {{4}}
                                ]
                            }
                        ]
                    }
                }

                headers = {
                    "Authorization": f"Bearer {ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                }
                _logger.info("WhatsApp Message sent: %s", payload)

                try:
                    response = requests.post(url, json=payload, headers=headers)
                    _logger.info("WhatsApp Cloud Status: %s", response.status_code)
                    _logger.info("WhatsApp Cloud Response: %s", response.text)

                    if response.status_code not in (200, 201):
                        raise Exception(f"WhatsApp API ERROR → {response.text}")

                except Exception as e:
                    _logger.error("WhatsApp Failed: %s", str(e))

                invoice.write({
                    'last_wa_message_date': today,
                    'reminder_count': invoice.reminder_count + 1
                })
                current_dt = datetime.datetime.now()
                message = (
                    f"Dear {invoice.partner_id.name} This is a kind reminder that invoice {invoice.name} with an amount of was {str(invoice.amount_residual)} was due on {invoice.invoice_date_due.strftime('%Y-%m-%d')}.Please make the payment at your earliest convenience.!"
                )

                res = request.env['whatsapp.history'].sudo().create(
                    {
                        'message': message,
                        'message_id': "",
                        'author_id': user_partner.id,
                        'type': 'delivered',
                        'partner_id': invoice.partner_id.id,
                        'phone': invoice.partner_id.mobile,
                        'attachment_ids': "",
                        'provider_id': provider.id,
                        'company_id': provider.company_id.id,
                        'date': current_dt
                    })

                print("✅ WhatsApp reminder sent for invoice", invoice.id)

            except Exception as e:
                print("❌ ERROR:", e)
                _logger.error("WhatsApp reminder failed for invoice %s: %s", invoice.id, e)
