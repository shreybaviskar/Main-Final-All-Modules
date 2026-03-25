# -*- coding: utf-8 -*-
# from odoo import http


# class CustomSmsTemplates(http.Controller):
#     @http.route('/custom_sms_templates/custom_sms_templates', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_sms_templates/custom_sms_templates/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_sms_templates.listing', {
#             'root': '/custom_sms_templates/custom_sms_templates',
#             'objects': http.request.env['custom_sms_templates.custom_sms_templates'].search([]),
#         })

#     @http.route('/custom_sms_templates/custom_sms_templates/objects/<model("custom_sms_templates.custom_sms_templates"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_sms_templates.object', {
#             'object': obj
#         })
