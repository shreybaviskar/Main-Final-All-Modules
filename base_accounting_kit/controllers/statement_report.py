# -*- coding: utf-8 -*-
import json
import inspect
from odoo import http
from odoo.http import content_disposition, request
from odoo.tools import html_escape


class XLSXReportController(http.Controller):
    """ Controller for xlsx report capable of routing for multiple Cybrosys modules """

    @http.route('/xlsx_report', type='http', auth='user', methods=['POST'], csrf=False)
    def get_report_xlsx(self, model=None, data=None, output_format='xlsx', report_name='Report', report_action=None,
                        options=None, **kw):
        """ Get xlsx report data """
        uid = request.session.uid
        report_obj = request.env[model].with_user(uid)

        try:
            if output_format == 'xlsx':
                response = request.make_response(
                    None, headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition(report_name + '.xlsx'))])

                # BULLETPROOF ROUTING: Inspect the target method to see what arguments it requires
                method_sig = inspect.signature(report_obj.get_xlsx_report)
                params = method_sig.parameters

                # Check if the target model expects 'report_name' and 'report_action'
                if 'report_name' in params and 'report_action' in params:
                    # It's a dynamic_accounts_report style model.
                    # Use 'data' if it exists, otherwise use 'options'.
                    payload = data if data else options
                    report_obj.get_xlsx_report(payload, response, report_name, report_action)
                else:
                    # It's a base_accounting_kit style model.
                    if isinstance(options, str):
                        opts = json.loads(options)
                    else:
                        opts = options or {}
                    report_obj.sudo().get_xlsx_report(opts, response)

                response.set_cookie('fileToken', 'dummy token')
                return response

        except Exception as event:
            serialize = http.serialize_exception(event)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': serialize
            }
            return request.make_response(html_escape(json.dumps(error)))