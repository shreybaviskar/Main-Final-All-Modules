import ast
import base64
import re
import requests

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError


class WAComposer(models.TransientModel):
    _name = 'wa.compose.message'
    _description = 'Whatsapp composition wizard'

    # @api.model
    # def default_get(self, fields):
    #     result = super(WAComposer, self).default_get(fields)
    #     active_model = False
    #     active_id = False
    #     template_domain = [('state', '=', 'added')]
    #     # Multi Companies and Multi Providers Code Here
    #     if self.env.user:
    #         provider_id = self.env.user.provider_ids.filtered(lambda x: x.company_id == self.env.company)
    #         if provider_id:
    #             result['provider_id'] = provider_id[0].id
    #             template_domain += [('provider_id', '=', provider_id[0].id)]
    #         else:
    #             template = self.env['wa.template'].browse(result.get('template_id'))
    #             provider_id = template.provider_id
    #             result['provider_id'] = provider_id.id
    #             template_domain += [('provider_id', '=', provider_id.id)]

    #     if 'model' in result:
    #         active_model = result.get('model')
    #         active_id = result.get('res_id')
    #     else:
    #         active_model = self.env.context.get('active_model')
    #         active_id = self.env.context.get('active_id')
    #     if active_model:
    #         record = self.env[active_model].browse(active_id)
    #         if 'template_id' in result:
    #             template = self.env['wa.template'].browse(result.get('template_id'))
    #             result['body'] = template._render_field('body_html', [record.id], compute_lang=True)[
    #                 record.id]
    #         if active_model == 'res.partner':
    #             result['partner_id'] = record.id
    #         else:
    #             if record._fields.get('partner_id'):
    #                 result['partner_id'] = record.partner_id and record.partner_id.id or False
    #             else:
    #                 if self.env.context.get('default_partner_id'):
    #                     result['partner_id'] = self.env.context.get('default_partner_id')
    #                 else:
    #                     result['partner_id'] = False
    #         if 'report' in self.env.context:
    #             report = str(self.env.context.get('report'))
    #             if active_model == 'event.registration':
    #                 pdf = self.env['ir.actions.report']._render_qweb_pdf(report, record.id)
    #             else:
    #                 pdf = self.env['ir.actions.report']._render_qweb_pdf(report, record.id)
    #             Attachment = self.env['ir.attachment'].sudo()
    #             b64_pdf = base64.b64encode(pdf[0])
    #             name = ''
    #             if active_model == 'res.partner':
    #                 if report == 'account_followup.action_report_followup':
    #                     name = 'Followups-%s' % record.id
    #             elif active_model == 'stock.picking':
    #                 name = ((record.state in ('done') and _('Delivery slip - %s') % record.name) or
    #                         _('Picking Operations - %s') % record.name)
    #             elif active_model == 'account.move':
    #                 name = ((record.state in ('posted') and record.name) or
    #                         _('Draft - %s') % record.name)
    #             elif active_model == 'event.registration':
    #                 name = (record.id or
    #                         _('Event - %s') % record.name)
    #             else:
    #                 name = ((record.state in ('draft', 'sent') and _('Quotation - %s') % record.name) or
    #                         _('Order - %s') % record.name)

    #             name = '%s.pdf' % name
    #             attac_id = Attachment.search([('name', '=', name)], limit=1)
    #             if report == 'account_followup.action_report_followup':
    #                 attac_id = Attachment
    #             if len(attac_id) == 0:
    #                 attac_id = Attachment.create({'name': name,
    #                                               'type': 'binary',
    #                                               'datas': b64_pdf,
    #                                               'res_model': active_model if active_model else 'whatsapp.history',
    #                                               })
    #             if active_model == 'res.partner':
    #                 result['partner_id'] = record.id
    #             else:
    #                 if record._fields.get('partner_id'):
    #                     result['partner_id'] = record.partner_id.id
    #                 elif self.env.context.get('default_partner_id'):
    #                     partner = self.env['res.partner'].browse(self.env.context.get('default_partner_id'))
    #                     result['partner_id'] = partner.id
    #                 else:
    #                     result['partner_id'] = False
    #             result['attachment_ids'] = [(4, attac_id.id)]
    #     if active_model or self.env.context.get('default_model'):
    #         model = active_model or self.env.context.get('default_model')
    #         template_domain += [('model', '=', model)]
    #     template_ids = self.template_id.search(template_domain)
    #     self.domain_template_ids = [(6, 0, template_ids.ids)]
    #     return result

    # Sale And Invoice Whatsapp Report default
    # @api.model
    # def default_get(self, fields):
    #     result = super(WAComposer, self).default_get(fields)

    #     active_model = False
    #     active_id = False
    #     template_domain = [('state', '=', 'added')]

    #     # -------------------------------------------------
    #     # Provider logic
    #     # -------------------------------------------------
    #     if self.env.user:
    #         provider_id = self.env.user.provider_ids.filtered(
    #             lambda x: x.company_id == self.env.company
    #         )
    #         if provider_id:
    #             result['provider_id'] = provider_id[0].id
    #             template_domain += [('provider_id', '=', provider_id[0].id)]
    #         else:
    #             template = self.env['wa.template'].browse(result.get('template_id'))
    #             if template:
    #                 result['provider_id'] = template.provider_id.id
    #                 template_domain += [('provider_id', '=', template.provider_id.id)]

    #     # -------------------------------------------------
    #     # Active model / id
    #     # -------------------------------------------------
    #     if 'model' in result:
    #         active_model = result.get('model')
    #         active_id = result.get('res_id')
    #     else:
    #         active_model = self.env.context.get('active_model')
    #         active_id = self.env.context.get('active_id')

    #     # -------------------------------------------------
    #     # Main logic
    #     # -------------------------------------------------
    #     if active_model and active_id:
    #         record = self.env[active_model].browse(active_id)

    #         # ---------------- Body from template ----------------
    #         if result.get('template_id'):
    #             template = self.env['wa.template'].browse(result.get('template_id'))
    #             result['body'] = template._render_field(
    #                 'body_html', [record.id], compute_lang=True
    #             )[record.id]

    #         # ---------------- Partner ----------------
    #         if active_model == 'res.partner':
    #             result['partner_id'] = record.id
    #         elif record._fields.get('partner_id'):
    #             result['partner_id'] = record.partner_id.id if record.partner_id else False
    #         else:
    #             result['partner_id'] = self.env.context.get('default_partner_id')

    #         # -------------------------------------------------
    #         # REPORT ATTACHMENT (DEFAULT ODOO REPORT)
    #         # -------------------------------------------------
    #         report = False

    #         if active_model == 'sale.order':
    #             # ✅ Odoo default Sale Order / Quotation report
    #             report = 'sale.action_report_saleorder'

    #         elif 'report' in self.env.context:
    #             report = str(self.env.context.get('report'))

    #         if report:
    #             pdf = self.env['ir.actions.report']._render_qweb_pdf(
    #                 report, record.id
    #             )

    #             Attachment = self.env['ir.attachment'].sudo()
    #             b64_pdf = base64.b64encode(pdf[0])

    #             # ---------------- Filename (FIXED) ----------------
    #             if active_model == 'sale.order':
    #                 name = (
    #                     (record.state in ('draft', 'sent') and
    #                     _('Quotation - %s') % record.name)
    #                     or _('Order - %s') % record.name
    #                 )

    #             elif active_model == 'account.move':
    #                 # ✅ Invoice number instead of model name
    #                 if record.name and record.name != '/':
    #                     name = record.name
    #                 else:
    #                     name = _('Draft Invoice')

    #             else:
    #                 name = '%s-%s' % (active_model, record.id)

    #             name = '%s.pdf' % name

    #             attac_id = Attachment.create({
    #                 'name': name,
    #                 'type': 'binary',
    #                 'datas': b64_pdf,
    #                 'res_model': active_model,
    #                 'res_id': record.id,
    #             })

    #             result['attachment_ids'] = [(4, attac_id.id)]

    #     # -------------------------------------------------
    #     # Template domain
    #     # -------------------------------------------------
    #     if active_model or self.env.context.get('default_model'):
    #         model = active_model or self.env.context.get('default_model')
    #         template_domain += [('model', '=', model)]

    #     template_ids = self.env['wa.template'].search(template_domain)
    #     self.domain_template_ids = [(6, 0, template_ids.ids)]

    #     return result



    
    # Sale And Invoice Whatsapp Report Custome

    @api.model
    def default_get(self, fields):
        result = super(WAComposer, self).default_get(fields)

        active_model = False
        active_id = False
        template_domain = [('state', '=', 'added')]

        # ---------------- Provider logic ----------------
        if self.env.user:
            provider_id = self.env.user.provider_ids.filtered(
                lambda x: x.company_id == self.env.company
            )
            if provider_id:
                result['provider_id'] = provider_id[0].id
                template_domain.append(('provider_id', '=', provider_id[0].id))
            else:
                template = self.env['wa.template'].browse(result.get('template_id'))
                if template:
                    result['provider_id'] = template.provider_id.id
                    template_domain.append(('provider_id', '=', template.provider_id.id))

        # ---------------- Active model / id ----------------
        if 'model' in result:
            active_model = result.get('model')
            active_id = result.get('res_id')
        else:
            active_model = self.env.context.get('active_model')
            active_id = self.env.context.get('active_id')

        # ---------------- Main Logic ----------------
        if active_model and active_id:
            record = self.env[active_model].browse(active_id)

            # Body from template
            if result.get('template_id'):
                template = self.env['wa.template'].browse(result.get('template_id'))
                result['body'] = template._render_field(
                    'body_html', [record.id], compute_lang=True
                )[record.id]

            # Partner
            if active_model == 'res.partner':
                result['partner_id'] = record.id
            elif record._fields.get('partner_id'):
                result['partner_id'] = record.partner_id.id if record.partner_id else False
            else:
                result['partner_id'] = self.env.context.get('default_partner_id')

            # ---------------- REPORT ATTACHMENT ----------------
            report_xmlid = False

            if active_model == 'sale.order':
                # ✅ Custom Sale Order Report
                report_xmlid = 'aretx_workshop.action_sale_order_with_header'

            elif active_model == 'account.move':
                # ✅ Custom Invoice Report
                report_xmlid = 'aretx_workshop.action_report_custom_with_invoice'

            elif self.env.context.get('report'):
                report_xmlid = self.env.context.get('report')

            if report_xmlid:
                # Fallback to default reports if custom xmlid doesn't exist
                if not self.env.ref(report_xmlid, raise_if_not_found=False):
                    if active_model == 'sale.order':
                        report_xmlid = 'sale.action_report_saleorder'
                    elif active_model == 'account.move':
                        report_xmlid = 'account.account_invoices'

                Attachment = self.env['ir.attachment'].sudo()

                if active_model == 'sale.order':
                    name = _('Sale Order - %s') % record.name
                elif active_model == 'account.move':
                    name = _('Invoice - %s') % record.name
                elif active_model == 'stock.picking':
                    name = _('Delivery Slip - %s') % record.name
                else:
                    name = '%s-%s' % (active_model, record.id)

                name = '%s.pdf' % name

                attachment = Attachment.search([
                    ('name', '=', name), ('res_model', '=', active_model), ('res_id', '=', record.id)
                ], limit=1)

                if not attachment:
                    pdf = self.env['ir.actions.report']._render_qweb_pdf(report_xmlid, res_ids=record.id)
                    b64_pdf = base64.b64encode(pdf[0])
                    attachment = Attachment.create({
                        'name': name, 'type': 'binary', 'datas': b64_pdf,
                        'res_model': active_model, 'res_id': record.id,
                    })

                result['attachment_ids'] = [(4, attachment.id)]

        # ---------------- Template domain ----------------
        if active_model or self.env.context.get('default_model'):
            model = active_model or self.env.context.get('default_model')
            template_domain.append(('model', '=', model))

        template_ids = self.env['wa.template'].search(template_domain)
        self.domain_template_ids = [(6, 0, template_ids.ids)]

        return result


    body = fields.Html('Contents', default='', sanitize_style=True)
    partner_id = fields.Many2one('res.partner')
    template_id = fields.Many2one('wa.template', 'Use template', index=True)
    domain_template_ids = fields.Many2many(comodel_name='wa.template', string='domain template ids')
    attachment_ids = fields.Many2many('ir.attachment', 'wa_compose_message_ir_attachments_rel', 'wa_wizard_id',
                                      'attachment_id', 'Attachments')
    model = fields.Char('Related Document Model', index=True)
    res_id = fields.Integer('Related Document ID', index=True)
    provider_id = fields.Many2one('provider', 'Provider')
    company_ids = fields.Many2many('res.company', string='Company', default=lambda self: self.env.companies, required=True)
    allowed_provider_ids = fields.Many2many('provider', 'Provider', compute='update_allowed_providers')

    @api.depends('company_ids')
    def update_allowed_providers(self):
        self.allowed_provider_ids = self.env.user.provider_ids

    @api.onchange('company_ids', 'provider_id')
    def onchange_company_provider(self):
        self.template_id = False
        self.domain_template_ids = False
        domain = []
        if self.env.context.get('active_model') or self.env.context.get('default_model'):
            domain += [('model_id.model', '=', self.env.context.get('active_model') or self.env.context.get('default_model'))]
        if self.provider_id:
            domain += [('provider_id', '=', self.provider_id.id)]
        template_ids = self.template_id.search(domain)
        self.domain_template_ids = [(6, 0, template_ids.ids)]

    @api.onchange('template_id')
    def onchange_template_id_wrapper(self):
        self.ensure_one()
        if 'active_model' in self.env.context:
            active_model = str(self.env.context.get('active_model'))
            active_id = self.env.context.get('active_id') or self.env.context.get('active_ids')
            active_record = self.env[active_model].browse(active_id)
            for record in self:
                if record.template_id:
                    if record.template_id.components_ids.filtered(lambda comp: comp.type == 'body'):
                        variables_ids = record.template_id.components_ids.variables_ids
                        if variables_ids:
                            temp_body = tools.html2plaintext(record.template_id.body_html)
                            variables_length = len(record.template_id.components_ids.variables_ids)
                            for length, variable in zip(range(variables_length), variables_ids):
                                st = '{{%d}}' % (length + 1)
                                if variable.field_id.model == active_model or variable.free_text:
                                    value = active_record.read()[0][
                                        variable.field_id.name] if variable.field_id.name else variable.free_text
                                    if isinstance(value, tuple):
                                        value = value[1]
                                        temp_body = temp_body.replace(st, str(value))
                                    else:
                                        temp_body = temp_body.replace(st, str(value))
                            record.body = tools.plaintext2html(temp_body)
                        else:
                            record.body = \
                                record.template_id._render_field('body_html', [active_record.id], compute_lang=True)[
                                    active_record.id]

                else:
                    record.body = ''
        else:
            active_record = self.env[self.model].browse(self.res_id)
            for record in self:
                if record.template_id:
                    record.body = record.template_id._render_field('body_html', [active_record.id], compute_lang=True)[
                        active_record.id]
                else:
                    record.body = ''

    def send_whatsapp_message(self):
        if not (self.body or self.template_id or self.attachment_ids):
            return {}

        active_model = self.model if self.model else str(self.env.context.get('active_model'))
        active_id = self.res_id if self.res_id else self.env.context.get('active_id')
        record = self.env[active_model].browse(active_id)
        if active_model in ['sale.order', 'purchase.order']:
            record.filtered(lambda s: s.state == 'draft').write({'state': 'sent'})

        # Multi Companies and Multi Providers Code Here
        channel = self.provider_id.get_channel_whatsapp(self.partner_id, self.env.user)

        if channel:
            message_values = {
                'body': tools.html2plaintext(self.body) if self.body else '',
                'author_id': self.env.user.partner_id.id,
                'email_from': self.env.user.partner_id.email or '',
                'model': active_model,
                'message_type': 'wa_msgs',
                'isWaMsgs': True,
                'subtype_id': self.env['ir.model.data'].sudo()._xmlid_to_res_id('mail.mt_comment'),
                'partner_ids': [(4, self.env.user.partner_id.id)],
                'res_id': active_id,
                'reply_to': self.env.user.partner_id.email,
                'attachment_ids': [(4, attac_id.id) for attac_id in self.attachment_ids],
            }
            context_vals = {'provider_id': self.provider_id}
            if self.template_id:
                context_vals.update({'template_send': True, 'wa_template': self.template_id, 'active_model_id': active_id,
                                     'active_model': active_model, 'partner_id': self.env.context.get('partner_id') or self.partner_id.id,
                                     'attachment_ids': self.attachment_ids})
            if self.env.context.get('booking_id'):
                context_vals.update({'booking_id':self.env.context.get('booking_id')})
            if self.env.context.get('is_automated_action'):
                context_vals.update({'is_automated_action':self.env.context.get('is_automated_action')})
            if self.env.context.get('report_taken'):
                context_vals.update({'report_taken':self.env.context.get('report_taken')})

            mail_message = self.env['mail.message'].sudo().with_context(context_vals).create(
                message_values)
            channel._notify_thread(mail_message, message_values)



