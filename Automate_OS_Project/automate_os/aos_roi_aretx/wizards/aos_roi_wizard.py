from odoo import models, fields, api
import io
import base64
import csv

try:
    import xlsxwriter
except Exception:
    xlsxwriter = None


class AosRoiWizard(models.TransientModel):
    _name = "aos.roi.wizard"
    _description = "ROI Excel Generator"

    new_invoices_per_month = fields.Integer(
        string="No of Invoices per month", required=True, default=60
    )
    avg_cost = fields.Float(
        string="Avg Cost of Alignment and Balancing", required=True, default=1500.0
    )
    percentage_returning = fields.Float(
        string="Percentage of Returning Customers", required=True, default=15.0
    )
    file = fields.Binary(string="File", readonly=True)
    filename = fields.Char(string="Filename")

    def action_generate_excel(self):
        self.ensure_one()
        months = 60
        # treat invoice counts as integers
        new_value = float(self.new_invoices_per_month)
        pct = float(self.percentage_returning) / 100.0
        avg = float(self.avg_cost)

        # prepare rows: month, new, returning(after 3 months using total visits of (m-3)), total, monthly_additional
        rows = []
        new_list = [new_value] * months
        total_list = []  # stores total visits per month as they are computed
        for i in range(1, months + 1):
            new = new_list[i - 1]
            if i > 3:
                # use the total visits from month (i-3) to calculate returning customers
                returning = float(round(total_list[i - 4] * pct))
            else:
                returning = 0
            total = float(round(new)) + float(round(returning))
            # monthly additional revenue as integer
            monthly_additional = float(round(avg * returning))
            rows.append([i, new, returning, total, monthly_additional])
            total_list.append(total)

        # write Excel or CSV fallback
        if xlsxwriter:
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {"in_memory": True})
            ws = workbook.add_worksheet("ROI")
            header = [
                "Month",
                "New invoices per month",
                "Returning (after 3 months)",
                "Total visits",
                "Monthly additional revenue",
            ]
            header_fmt = workbook.add_format({"bold": True})
            money_fmt = workbook.add_format({"num_format": "#,##0.00"})
            ws.write_row(0, 0, header, header_fmt)
            rownum = 1
            for r in rows:
                ws.write_number(rownum, 0, int(r[0]))
                ws.write_number(rownum, 1, r[1])
                ws.write_number(rownum, 2, r[2])
                ws.write_number(rownum, 3, r[3])
                ws.write_number(rownum, 4, r[4])
                rownum += 1
            workbook.close()
            data = output.getvalue()
            filename = f"ROI_{months}_months.xlsx"
        else:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                [
                    "Month",
                    "New invoices per month",
                    "Returning (after 3 months)",
                    "Total visits",
                    "Monthly additional revenue",
                ]
            )
            for r in rows:
                writer.writerow(r)
            data = output.getvalue().encode("utf-8")
            filename = f"ROI_{months}_months.csv"

        self.filename = filename
        self.file = base64.b64encode(data)

        # store the generated file in aos.roi.file
        file_obj = self.env['aos.roi.file'].create({
            'name': filename,
            'file': base64.b64encode(data),
        })

        # Return the wizard form in the current window so the user remains on the form.
        # The generated file is available via the 'file' binary field on the form.
        return {
            "type": "ir.actions.act_window",
            "res_model": "aos.roi.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

