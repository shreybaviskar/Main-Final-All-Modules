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
import certifi


_logger = logging.getLogger(__name__)


class TyreServiceReminder(models.Model):
    _name = 'tyre.service.reminder'
    _description = 'Tyre Service Reminder Cron'

    # preffered
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

    #production
    @api.model
    def _cron_tyre_service_reminder(self, account_type=2):

        ir_config = self.env['ir.config_parameter'].sudo()
        km_limit = int(ir_config.get_param('tyreshop.tyre_message_km', default=5000))
        month_limit = int(ir_config.get_param('tyreshop.tyre_message_months', default=3))

        today = fields.Date.today()
        current_dt = fields.Datetime.now()

        Vehicle = self.env['vehicle.master.model'].sudo()
        Log = self.env['aretx.sms.cron.log'].sudo()

        vehicles = Vehicle.search([('x_avg_km', '>', 0)])
        template = self.env['custom.sms.templates'].browse(1)

        if not template:
            _logger.error("SMS Template not found.")
            return

        for vehicle in vehicles:

            try:
                partner = vehicle.x_customer_id
                if not partner:
                    continue

                phone = partner.mobile or partner.phone
                if not phone:
                    Log.create({
                        'res_model': 'vehicle.master.model',
                        'res_id': vehicle.id,
                        'vehicle_id': vehicle.id,
                        'partner_id': partner.id,
                        'phone': '',
                        'message': 'Phone missing',
                        'delivery_status': 'skipped',
                        'error_message': 'Missing mobile/phone',
                    })
                    continue

                clean_phone = str(phone).replace("+91", "").replace(" ", "").strip()


                last_date = vehicle.last_message_date

                if not last_date and vehicle.create_date:
                    last_date = vehicle.create_date.date()
                elif not last_date:
                    last_date = today

                days_since_last = (today - last_date).days
                months_since_last = days_since_last / 30.0
                expected_km = vehicle.x_avg_km * months_since_last

                km_due = expected_km >= km_limit
                month_due = months_since_last >= month_limit

                if not (km_due or month_due):
                    Log.create({
                        'res_model': 'vehicle.master.model',
                        'res_id': vehicle.id,
                        'vehicle_id': vehicle.id,
                        'partner_id': partner.id,
                        'phone': phone,
                        'message': 'Service not due yet',
                        'delivery_status': 'skipped',
                    })
                    continue

                # Build Template Message
                message = template.description or ''

                message = message.replace("%partner_name%", partner.name or "")
                message = message.replace(
                    "%vehicle_x_vehicle_number_id%",
                    vehicle.x_vehicle_number_id or ""
                )
                message = message.replace(
                    "%vehicle_x_avg_km%",
                    str(int(expected_km))
                )

                partner.message_post(body=message)
                vehicle.last_message_date = today


                log_record = Log.create({
                    'res_model': 'vehicle.master.model',
                    'res_id': vehicle.id,
                    'vehicle_id': vehicle.id,
                    'partner_id': partner.id,
                    'phone': phone,
                    'template_id': template.id,
                    'message': message,
                    'delivery_status': 'failed',  # default until proven success
                })

                # Create Composer Record
                composer = self.env['aretx.sms.composer'].sudo().create({
                    'res_model': 'vehicle.master.model',
                    'res_id': vehicle.id,
                    'number': phone,
                    'number_field_name': 'phone',
                    'partner_id': partner.id,
                    'vehicle_id': vehicle.id,
                    'template_id': template.id,
                    'title': template.name,
                    'content': message,
                    'recipient_single_number_itf': phone,
                    'vehicle_number': vehicle.x_vehicle_number_id,
                    'is_vehicle': 1,
                })


                # sms api
                query = self.env['custom.sms.setting'].browse(1)
                query.ensure_one()

                data = {
                    query.userid_map: query.userid,
                    query.userid_password_map: query.userpassword,
                    query.account_type_map: account_type,
                    query.phonenumber_map: clean_phone,
                    query.msg_map: message,
                    query.gsm_map: query.gsm_sendername,
                }

                response = requests.get(query.send_url, data)

                error_list = [
                    "Invalid Template",
                    "Authentication Fail",
                    "Invalid Sender ID",
                    "Error :- Object reference not set to an instance of an object.",
                    "No Data Found"
                ]


                response_text = response.text.strip()

                is_success = (
                        response.status_code == 200
                        and response_text.isdigit()
                )

                if is_success:

                    composer.write({
                        'msg_id': response_text,
                        'log_date': datetime.datetime.now().strftime("%d %B %Y"),
                        'delivery_status': 0,
                    })

                    log_record.write({
                        'delivery_status': 'sent',
                        'msg_id': response_text,
                    })

                else:

                    composer.write({
                        'error_log_status': response.status_code,
                        'error_log_text': response_text,
                    })

                    log_record.write({
                        'delivery_status': 'failed',
                        'error_message': response_text,
                    })

            except Exception as e:

                _logger.exception("Tyre SMS Cron Unexpected Error")

                Log.create({
                    'res_model': 'vehicle.master.model',
                    'res_id': vehicle.id,
                    'vehicle_id': vehicle.id,
                    'partner_id': vehicle.x_customer_id.id if vehicle.x_customer_id else False,
                    'phone': '',
                    'message': 'Unexpected Exception',
                    'delivery_status': 'failed',
                    'error_message': str(e),
                })

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

    #latest
    @api.model
    def _cron_tyre_service_wa_reminder(self):
        """Send WhatsApp tyre service reminders using direct Graph API (old style)."""

        ir_config = self.env['ir.config_parameter'].sudo()

        km_limit = int(ir_config.get_param('tyreshop.tyre_message_km', default=5000))
        month_limit = int(ir_config.get_param('tyreshop.tyre_message_months', default=3))

        today = fields.Date.today()
        current_dt = fields.Datetime.now()

        Vehicle = self.env['vehicle.master.model'].sudo()
        Log = self.env['wa.cron.log'].sudo()

        vehicles = Vehicle.search([('x_avg_km', '>', 0)])

        # -----------------------------------------
        # Fetch Provider (OLD STYLE)
        # -----------------------------------------
        company_id = self.env.company.id

        provider = self.env['provider'].sudo().search([
            ('company_id', '=', company_id),
        ], limit=1)

        if not provider:
            _logger.error("No provider found for company %s", company_id)
            return

        user_partner = provider.user_id.partner_id
        PHONE_NUMBER_ID = provider.graph_api_instance_id
        ACCESS_TOKEN = provider.graph_api_token

        if not PHONE_NUMBER_ID or not ACCESS_TOKEN:
            _logger.error("Provider missing Graph API credentials")
            return

        url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

        # -----------------------------------------
        # Loop Vehicles
        # -----------------------------------------
        for vehicle in vehicles:

            partner = vehicle.x_customer_id

            if not partner or not (partner.mobile or partner.phone):
                Log.create({
                    'message': 'Partner or phone missing',
                    'vehicle_id': vehicle.id,
                    'partner_id': partner.id if partner else False,
                    'phone': '',
                    'status': 'skipped',
                    'api_response': 'Missing partner or phone',
                    'date': current_dt,
                })
                continue

            phone = partner.mobile or partner.phone

            # -----------------------
            # Date Logic
            # -----------------------
            last_date = vehicle.last_wa_message_date

            if not last_date and vehicle.create_date:
                last_date = vehicle.create_date.date()
            elif not last_date:
                last_date = today

            days_since_last = (today - last_date).days
            months_since_last = days_since_last / 30.0
            expected_km = vehicle.x_avg_km * months_since_last

            km_due = expected_km >= km_limit
            month_due = months_since_last >= month_limit

            if not (km_due or month_due):
                Log.create({
                    'message': 'Service not due yet',
                    'vehicle_id': vehicle.id,
                    'partner_id': partner.id,
                    'phone': phone,
                    'status': 'skipped',
                    'api_response': 'Not due',
                    'date': current_dt,
                })
                continue

            # Build Message
            message = (
                f"Dear {partner.name}, "
                f"your vehicle ({vehicle.x_vehicle_number_id or ''}) "
                f"has run approximately {int(expected_km)} KM. "
                f"It's time for a tyre service check."
            )

            # Clean phone (IMPORTANT)
            clean_phone = phone.replace("+", "").replace(" ", "").strip()

            payload = {
                "messaging_product": "whatsapp",
                "to": clean_phone,
                "type": "template",
                "template": {
                    "name": "reminder_service",
                    "language": {"code": "en"},
                    "components": [{
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": partner.name or ""},
                            {"type": "text", "text": vehicle.x_vehicle_number_id or ""},
                            {"type": "text", "text": str(int(expected_km))},
                        ]
                    }]
                }
            }

            headers = {
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "Content-Type": "application/json",
            }

            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    verify=certifi.where()
                )

                _logger.info("WhatsApp Status: %s", response.status_code)
                _logger.info("WhatsApp Response: %s", response.text)

                if response.status_code not in (200, 201):
                    Log.create({
                        'message': message,
                        'vehicle_id': vehicle.id,
                        'partner_id': partner.id,
                        'phone': phone,
                        'author_id': user_partner.id,
                        'provider_id': provider.id,
                        'company_id': provider.company_id.id,
                        'status': 'failed',
                        'api_response': response.text,
                        'date': current_dt,
                    })
                    continue

                vehicle.write({
                    'last_wa_message_date': today,
                })

                Log.create({
                    'message': message,
                    'vehicle_id': vehicle.id,
                    'partner_id': partner.id,
                    'phone': phone,
                    'author_id': user_partner.id,
                    'provider_id': provider.id,
                    'company_id': provider.company_id.id,
                    'status': 'success',
                    'api_response': response.text,
                    'date': current_dt,
                })

                # Optional: also create WhatsApp history record manually
                self.env['whatsapp.history'].sudo().create({
                    'message': message,
                    'message_id': '',
                    'author_id': user_partner.id,
                    'type': 'sent',
                    'partner_id': partner.id,
                    'phone': phone,
                    'provider_id': provider.id,
                    'company_id': provider.company_id.id,
                    'date': current_dt,
                })

            except Exception as e:

                Log.create({
                    'message': message,
                    'vehicle_id': vehicle.id,
                    'partner_id': partner.id,
                    'phone': phone,
                    'status': 'failed',
                    'api_response': str(e),
                    'date': current_dt,
                })

                _logger.error("WhatsApp Cron Error: %s", str(e))


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

    # updated code with logger
    @api.model
    def _cron_send_payment_wa_reminder(self):

        ir_config = self.env['ir.config_parameter'].sudo()
        reminder_message_payment_days = int(
            ir_config.get_param('tyreshop.reminder_message_payment_days', default=3)
        )

        today = date.today()
        current_dt = fields.Datetime.now()

        Log = self.env['wa.cron.log'].sudo()

        overdue_invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', '!=', 'paid'),
            ('invoice_date_due', '<=', today),
        ])

        template = self.env['wa.template'].search([
            ('name', '=', 'reminder_payment')
        ], limit=1)

        for invoice in overdue_invoices:

            partner = invoice.partner_id
            phone = partner.mobile or partner.phone

            # ----------------------------
            # Skip if no phone
            # ----------------------------
            if not partner or not phone:
                Log.create({
                    'message': 'Partner or phone missing',
                    'partner_id': partner.id if partner else False,
                    'phone': phone or '',
                    'status': 'skipped',
                    'api_response': 'Missing partner or phone',
                    'date': current_dt,
                })
                continue

            last_reminder_date = invoice.last_wa_message_date or date(1999, 1, 1)

            is_due_today = today == invoice.invoice_date_due

            if last_reminder_date and \
                    (today - last_reminder_date).days < reminder_message_payment_days and \
                    (is_due_today is False):
                Log.create({
                    'message': 'Skipped due to frequency control',
                    'partner_id': partner.id,
                    'phone': phone,
                    'status': 'skipped',
                    'api_response': 'Too soon since last reminder',
                    'date': current_dt,
                })
                continue

            try:
                # ---------------- PDF PART (UNCHANGED) ----------------
                attachment = self.env['ir.attachment'].search([
                    ('res_model', '=', 'account.move'),
                    ('res_id', '=', invoice.id),
                    ('mimetype', '=', 'application/pdf'),
                ], limit=1)

                if not attachment:
                    report = self.env.ref("account.account_invoices")
                    pdf_content, _ = report._render_qweb_pdf([invoice.id])

                    pdf_base64 = base64.b64encode(pdf_content)

                    attachment = self.env['ir.attachment'].sudo().create({
                        'name': f"{invoice.name}.pdf",
                        'type': 'binary',
                        'datas': pdf_base64,
                        'mimetype': 'application/pdf',
                        'public': True,
                        'res_model': 'account.move',
                        'res_id': invoice.id,
                    })

                attachment.generate_access_token()

                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                pdf_url = f"{base_url}/web/content/{attachment.id}"

                provider = self.env['provider'].search(
                    [('company_id', '=', invoice.company_id.id)],
                    limit=1
                )

                if not provider:
                    Log.create({
                        'message': 'Provider not found',
                        'partner_id': partner.id,
                        'phone': phone,
                        'status': 'failed',
                        'api_response': 'No provider configured',
                        'date': current_dt,
                    })
                    continue

                graph_api_instance_id = provider.graph_api_instance_id
                user_partner = provider.user_id.partner_id
                graph_api_token = provider.graph_api_token

                PHONE_NUMBER_ID = graph_api_instance_id
                ACCESS_TOKEN = graph_api_token

                url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

                clean_phone = phone.replace("+91", "").replace(" ", "").strip()

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
                                "parameters": [{
                                    "type": "document",
                                    "document": {
                                        "link": pdf_url,
                                        "filename": invoice.name
                                    }
                                }]
                            },
                            {
                                "type": "body",
                                "parameters": [
                                    {"type": "text", "text": invoice.partner_id.name},
                                    {"type": "text", "text": invoice.name},
                                    {"type": "text", "text": str(invoice.amount_residual)},
                                    {"type": "text", "text": invoice.invoice_date_due.strftime('%Y-%m-%d')},
                                ]
                            }
                        ]
                    }
                }

                headers = {
                    "Authorization": f"Bearer {ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                }

                response = requests.post(url, json=payload, headers=headers)

                # -------------------------
                # FAILURE LOG
                # -------------------------
                if response.status_code not in (200, 201):
                    Log.create({
                        'message': 'WhatsApp API failed',
                        'partner_id': partner.id,
                        'phone': phone,
                        'provider_id': provider.id,
                        'company_id': provider.company_id.id,
                        'status': 'failed',
                        'api_response': response.text,
                        'date': current_dt,
                    })
                    continue

                # -------------------------
                # UPDATE INVOICE
                # -------------------------
                invoice.write({
                    'last_wa_message_date': today,
                    'reminder_count': invoice.reminder_count + 1
                })

                message = (
                    f"Dear {invoice.partner_id.name} "
                    f"This is a kind reminder that invoice {invoice.name} "
                    f"amount {str(invoice.amount_residual)} "
                    f"was due on {invoice.invoice_date_due.strftime('%Y-%m-%d')}."
                )

                # -------------------------
                # WhatsApp History
                # (ONLY FIX: replaced request.env with self.env)
                # -------------------------
                self.env['whatsapp.history'].sudo().create({
                    'message': message,
                    'message_id': "",
                    'author_id': user_partner.id,
                    'type': 'delivered',
                    'partner_id': invoice.partner_id.id,
                    'phone': phone,
                    'provider_id': provider.id,
                    'company_id': provider.company_id.id,
                    'date': current_dt
                })

                # -------------------------
                # SUCCESS LOG
                # -------------------------
                Log.create({
                    'message': message,
                    'partner_id': partner.id,
                    'phone': phone,
                    'provider_id': provider.id,
                    'company_id': provider.company_id.id,
                    'status': 'success',
                    'api_response': response.text,
                    'date': current_dt,
                })

            except Exception as e:

                Log.create({
                    'message': 'Exception during WhatsApp send',
                    'partner_id': partner.id if partner else False,
                    'phone': phone or '',
                    'status': 'failed',
                    'api_response': str(e),
                    'date': current_dt,
                })

                _logger.error(
                    "WhatsApp reminder failed for invoice %s: %s",
                    invoice.id, e
                )
