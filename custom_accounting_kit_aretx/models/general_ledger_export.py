import base64
import io
import xlsxwriter
import re
from datetime import datetime
from odoo import models, api

import logging
_logger = logging.getLogger(__name__)


class GeneralLedgerExport(models.TransientModel):
    _name = 'general.ledger.export'
    _description = 'General Ledger Export'

    def format_currency_helper(self, amount, currency_symbol, precision=2):
        if currency_symbol and currency_symbol != 'False':
            return f"{currency_symbol} {amount:,.{precision}f}"
        return f"{amount:,.{precision}f}"

    def _generate_gl_filename(self, data, file_ext="pdf"):
        _logger.info(f"Called filename function for {file_ext}")
        start_date = data.get('date_from')
        end_date = data.get('date_to')
        month = data.get('month')
        quarter = data.get('quarter')
        year = data.get('year')

        search_text = data.get('search_text', '').strip()
        search_prefix = ""
        if search_text:
            sanitized_text = search_text.replace(' ', '_').replace('/', '_').replace('\\', '_')
            search_prefix = f"{sanitized_text}_"

        _logger.info(start_date)
        _logger.info(end_date)
        _logger.info(quarter)
        _logger.info(month)
        _logger.info(year)

        filename_core = ""

        # Month + Year
        if month and year:
            date_obj = datetime(int(year), int(month), 1)
            filename_core = date_obj.strftime('%b_%Y')

        # Quarter + Year
        elif quarter and year:
            quarter_map = {
                "q1": "Jan_Mar",
                "q2": "Apr_Jun",
                "q3": "Jul_Sep",
                "q4": "Oct_Dec"
            }
            quarter_range = quarter_map.get(quarter.lower(), quarter.lower())
            filename_core = f"{quarter_range}_{year}"

        # Only Year
        elif year and not month and not quarter:
            filename_core = f"{year}"

        # Date range
        elif start_date and end_date:
            start_str = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d%m%Y")
            end_str = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d%m%Y")
            filename_core = f"{start_str}_{end_str}"

        # Default (timestamp)
        else:
            filename_core = datetime.now().strftime('%Y%m%d_%H%M%S')

        filename = f"general_ledger_{search_prefix}{filename_core}.{file_ext}"

        filename = filename.replace('__', '_')

        _logger.info(filename)
        return filename


    def get_period_text(self, data):
        date_from = data.get("date_from")
        date_to = data.get("date_to")

        if date_from and date_to:
            try:
                from_str = datetime.strptime(date_from, "%Y-%m-%d").strftime("%d %b %Y")
                to_str = datetime.strptime(date_to, "%Y-%m-%d").strftime("%d %b %Y")
                _logger.info(f"Period: From {from_str} To {to_str}")
                return f"Period: From {from_str} To {to_str}"
            except Exception as e:
                _logger.error(f"Error generating Period Text: {str(e)}")

        # Fallback if dates are missing or parsing fails
        return f"Period: {data.get('filter_title', 'All Records')}"

    @api.model
    def export_general_ledger_pdf(self, data):
        """Export General Ledger to PDF using Odoo QWeb template"""

        if 'grouped_data' in data and isinstance(data['grouped_data'], dict):
            data['grouped_data'] = list(data['grouped_data'].values())

        if 'column_config' not in data:
            config = self.env['general.ledger.report.config'].get_active_config()
            data['column_config'] = config.get_column_config()

        data['format_currency'] = self.format_currency_helper

        filename = self._generate_gl_filename(data, file_ext="pdf")

        try:
            report_ref = 'custom_accounting_kit_aretx.general_ledger_pdf_export'
            report = self.env.ref(report_ref)

            pdf_content, _ = report._render_qweb_pdf(res_ids=[], data={'data': data})

            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'store_fname': filename,
                'mimetype': 'application/pdf',
            })
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self'
            }
        except Exception as e:
            # Alternative approach if the above doesn't work
            try:
                report_ref = 'custom_accounting_kit_aretx.general_ledger_pdf_export'
                report = self.env.ref(report_ref)

                # Alternative method call for Odoo 18
                pdf_content, _ = report._render_qweb_pdf(report_ref, data={'data': data})

                attachment = self.env['ir.attachment'].create({
                    'name': filename,
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'store_fname': filename,
                    'mimetype': 'application/pdf',
                })
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'/web/content/{attachment.id}?download=true',
                    'target': 'self'
                }
            except Exception as e2:
                return {
                    'type': 'ir.actions.report',
                    'report_name': 'custom_accounting_kit_aretx.general_ledger_pdf_export',
                    'data': {'data': data},
                    'report_type': 'qweb-pdf'
                }

    @api.model
    def export_general_ledger_xlsx(self, data):
        data['format_currency'] = self.format_currency_helper
        try:
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('General Ledger')

            # Enhanced formatting
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D3D3D3',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'font_size': 11
            })
            number_format = workbook.add_format({
                'num_format': '#,##0.00',
                'border': 1,
                'align': 'right',
                'valign': 'vcenter'
            })
            text_format = workbook.add_format({
                'border': 1,
                'align': 'left',
                'valign': 'vcenter',
                'text_wrap': True
            })
            title_format = workbook.add_format({
                'bold': True,
                'align': 'center',
                'font_size': 16,
                'bg_color': '#4F81BD',
                'font_color': 'white'
            })
            account_format = workbook.add_format({
                'bold': True,
                'bg_color': '#F0F8FF',
                'border': 1,
                'align': 'left',
                'valign': 'vcenter'
            })

            # Set column widths
            worksheet.set_column('A:A', 15)  # Journal
            worksheet.set_column('B:B', 12)  # Date
            worksheet.set_column('C:C', 25)  # Communication
            worksheet.set_column('D:D', 20)  # Partner
            worksheet.set_column('E:E', 10)  # Currency
            worksheet.set_column('F:F', 15)  # Debit
            worksheet.set_column('G:G', 15)  # Credit
            worksheet.set_column('H:H', 15)  # Balance

            period_text = self.get_period_text(data)

            # Title & filter info
            worksheet.merge_range('A1:H1', 'General Ledger Report', title_format)
            worksheet.merge_range(
                'A2:H2',
                period_text,
                workbook.add_format({'align': 'center', 'font_size': 12, 'italic': True})
            )

            # Add some spacing
            worksheet.set_row(2, 5)  # Empty row with reduced height

            # Headers
            headers = ['Journal', 'Date', 'Communication', 'Partner', 'Currency', 'Debit', 'Credit', 'Balance']
            for col, header in enumerate(headers):
                worksheet.write(4, col, header, header_format)

            # Ledger data
            row = 5
            grouped_data = data.get('grouped_data', {})
            ledger_data = data.get('ledger_data', [])

            # Organize data by account
            account_lines = {}
            for line in ledger_data:
                if 'account_id' in line and line['account_id']:
                    account_id = line['account_id'][0] if isinstance(line['account_id'], list) else line['account_id']
                    account_lines.setdefault(account_id, []).append(line)

            # Process each account
            for account_id, group in grouped_data.items():
                # Account header
                account_name = group.get('accountName', f'Account {account_id}')
                worksheet.merge_range(row, 0, row, 7, f"Account: {account_name}", account_format)

                row += 1

                # Account lines
                account_id_int = int(account_id) if str(account_id).isdigit() else account_id

                subtotal_debit = 0
                subtotal_credit = 0
                subtotal_balance = 0

                for line in account_lines.get(account_id_int, []):
                    # Skip zero lines except Initial Balance
                    if (line.get('debit', 0) == 0 and
                            line.get('credit', 0) == 0 and
                            line.get('balance', 0) == 0 and
                            line.get('move_name', '') != 'Initial Balance'):
                        continue

                    # Write line data
                    worksheet.write(row, 0, line.get('move_name', ''), text_format)
                    worksheet.write(row, 1, line.get('date', ''), text_format)
                    worksheet.write(row, 2, line.get('name', ''), text_format)

                    # Handle partner name
                    partner = ''
                    if line.get('partner_id'):
                        if isinstance(line['partner_id'], list) and len(line['partner_id']) > 1:
                            partner = line['partner_id'][1]
                        elif isinstance(line['partner_id'], str):
                            partner = line['partner_id']
                    worksheet.write(row, 3, partner, text_format)

                    # Handle currency
                    currency = ''
                    if line.get('currency_id'):
                        if isinstance(line['currency_id'], list) and len(line['currency_id']) > 1:
                            currency = line['currency_id'][1]
                        elif isinstance(line['currency_id'], str):
                            currency = line['currency_id']
                    worksheet.write(row, 4, currency, text_format)

                    debit = line.get('debit', 0)
                    credit = line.get('credit', 0)
                    balance = line.get('balance', 0)

                    worksheet.write(row, 5, debit, number_format)
                    worksheet.write(row, 6, credit, number_format)
                    worksheet.write(row, 7, balance, number_format)

                    subtotal_debit += debit
                    subtotal_credit += credit
                    subtotal_balance += balance

                    row += 1

                # Subtotal row for the account
                worksheet.merge_range(row, 0, row, 4, f"Total {account_name}", workbook.add_format({'bold': True, 'border': 1}))
                worksheet.write(row, 5, subtotal_debit, workbook.add_format({'num_format': '#,##0.00', 'bold': True, 'border': 1}))
                worksheet.write(row, 6, subtotal_credit, workbook.add_format({'num_format': '#,##0.00', 'bold': True, 'border': 1}))
                worksheet.write(row, 7, subtotal_balance, workbook.add_format({'num_format': '#,##0.00', 'bold': True, 'border': 1}))
                # Add spacing between accounts
                row += 2

            # Add summary at the end
            if grouped_data:
                total_debit = sum(group.get('totals', {}).get('debit', 0) for group in grouped_data.values())
                total_credit = sum(group.get('totals', {}).get('credit', 0) for group in grouped_data.values())
                total_balance = sum(group.get('totals', {}).get('balance', 0) for group in grouped_data.values())

                worksheet.merge_range(row, 0, row, 4, 'TOTAL',
                                      workbook.add_format(
                                          {'bold': True, 'bg_color': '#4F81BD', 'font_color': 'white', 'border': 1}))
                worksheet.write(row, 5, total_debit,
                                workbook.add_format({'num_format': '#,##0.00', 'bold': True, 'bg_color': '#4F81BD',
                                                     'font_color': 'white', 'border': 1}))
                worksheet.write(row, 6, total_credit,
                                workbook.add_format({'num_format': '#,##0.00', 'bold': True, 'bg_color': '#4F81BD',
                                                     'font_color': 'white', 'border': 1}))
                worksheet.write(row, 7, total_balance,
                                workbook.add_format({'num_format': '#,##0.00', 'bold': True, 'bg_color': '#4F81BD',
                                                     'font_color': 'white', 'border': 1}))

            workbook.close()
            output.seek(0)

            # filename = f"General_Ledger_{data.get('filter_title', 'Report')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filename = self._generate_gl_filename(data, file_ext="xlsx")

            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(output.read()),
                'store_fname': filename,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            })
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self'
            }

        except Exception as e:
            # Log the error and return user-friendly message

            _logger.error(f"Error exporting General Ledger to XLSX: {str(e)}")

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Error exporting to Excel: {str(e)}',
                    'type': 'danger',
                    'sticky': False,
                }
            }