from odoo import http
from odoo.http import request
import base64


class AosRoiController(http.Controller):
    @http.route('/aos-roi/webpage', type='http', auth='public', website=True, methods=['GET', 'POST'], csrf=False)
    def webpage(self, **post):
        """Render the public ROI form (GET) and generate the tables shown on the website."""
        # Defaults for GET
        defaults = {
            "new_invoices_per_month": 60,
            "avg_cost": 1500.0,
            "percentage_returning": 20,
            "first_year_cost": "29000",
            "annual_cost": "9500",
        }

        if request.httprequest.method == "POST":
            # parse submitted values with safe defaults
            try:
                new_invoices = int(post.get("new_invoices_per_month") or defaults["new_invoices_per_month"])
            except Exception:
                new_invoices = defaults["new_invoices_per_month"]
            try:
                avg_cost = float(post.get("avg_cost") or defaults["avg_cost"])
            except Exception:
                avg_cost = defaults["avg_cost"]
            try:
                pct = float(post.get("percentage_returning") or defaults["percentage_returning"])
            except Exception:
                pct = defaults["percentage_returning"]

            # Build monthly rows (numeric values) — same logic as the wizard
            months = 60
            new_value = float(new_invoices)
            pct_fraction = float(pct) / 100.0
            avg = float(avg_cost)
            monthly_rows = []
            new_list = [new_value] * months
            total_list = []
            for i in range(1, months + 1):
                new = new_list[i - 1]
                if i > 3:
                    returning = total_list[i - 4] * pct_fraction
                else:
                    returning = 0.0
                total = new + returning
                monthly_additional = avg * returning
                monthly_rows.append((i, new, returning, total, monthly_additional))
                total_list.append(total)

            # build HTML table for monthly data
            header_cols = [
                "Month",
                "Invoices Per Month",
                ("Returning Customers", "These are customers who visit your shop after receiving the message from AutomateOS system"),
                "Total visit",
                ("Additional revenue", "Revenue collected from customers who visited your shop after receiving message from AutomateOS system"),
            ]
            table_parts = ['<div class="table-responsive"><table class="table table-striped table-bordered aos-roi-table"><thead><tr>']
            for h in header_cols:
                if isinstance(h, tuple):
                    label, tooltip = h
                    table_parts.append(
                        f'<th>{label} <button type="button" class="aos-roi-info-icon" title="{tooltip}">&#9432;</button></th>'
                    )
                else:
                    table_parts.append(f"<th>{h}</th>")
            table_parts.append("</tr></thead><tbody>")
            for r in monthly_rows:
                table_parts.append("<tr>")
                table_parts.append(f"<td>{int(r[0])}</td>")
                table_parts.append(f"<td>{int(round(r[1]))}</td>")
                table_parts.append(f"<td>{int(round(r[2]))}</td>")
                table_parts.append(f"<td>{int(round(r[3]))}</td>")
                table_parts.append(
                    f"<td style='text-align:right;'>{int(round(r[4])):,}</td>"
                )
                table_parts.append("</tr>")
            table_parts.append("</tbody></table></div>")
            table_html = "".join(table_parts)

            # Read software cost inputs (may be empty)
            first_year_cost = None
            annual_cost = None
            try:
                if post.get("first_year_cost"):
                    first_year_cost = float(post.get("first_year_cost"))
                if post.get("annual_cost"):
                    annual_cost = float(post.get("annual_cost"))
            except Exception:
                first_year_cost = None
                annual_cost = None

            summary_html = None
            if first_year_cost is not None and annual_cost is not None:
                # monthly additional numeric list
                monthly_nums = [r[4] for r in monthly_rows]
                # cumulative additional revenue up to each year
                summary_parts = ['<div class="table-responsive"><table class="table table-striped table-bordered aos-roi-table aos-roi-summary-table"><thead><tr>']
                summary_parts.append("<th>Time Duration</th><th>Additional Revenue</th><th>Cost of Software</th><th>Return on Investment</th>")
                summary_parts.append("</tr></thead><tbody>")
                for year in range(1, 6):
                    end = year * 12
                    add_rev = sum(monthly_nums[:end])
                    cost = first_year_cost + (year - 1) * annual_cost
                    roi = (add_rev / cost) * 100.0 if cost > 0 else 0.0
                    summary_parts.append("<tr>")
                    summary_parts.append(f"<td>{year} Years</td>")
                    summary_parts.append(
                        f"<td style='text-align:right;'>{int(round(add_rev)):,}</td>"
                    )
                    summary_parts.append(
                        f"<td style='text-align:right;'>{int(round(cost)):,}</td>"
                    )
                    summary_parts.append(
                        f"<td style='text-align:right;'>{int(round(roi)):,}%</td>"
                    )
                    summary_parts.append("</tr>")
                summary_parts.append("</tbody></table></div>")
                summary_html = "".join(summary_parts)

            return request.render(
                "aos_roi_aretx.aos_roi_page_template",
                {
                    "new_invoices_per_month": new_invoices,
                    "avg_cost": avg_cost,
                    "percentage_returning": pct,
                    "table_html": table_html,
                    "summary_html": summary_html,
                    "first_year_cost": post.get("first_year_cost") or "29000",
                    "annual_cost": post.get("annual_cost") or "9500",
                },
            )

        # GET: render the website page with default values
        return request.render(
            "aos_roi_aretx.aos_roi_page_template",
            {
                "new_invoices_per_month": defaults["new_invoices_per_month"],
                "avg_cost": defaults["avg_cost"],
                "percentage_returning": defaults["percentage_returning"],
                "first_year_cost": defaults["first_year_cost"],
                "annual_cost": defaults["annual_cost"],
            },
        )
