from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ClaimReport(models.Model):
    _name = "claim.report"
    _description = "Claim Report"
    _order = "date desc, id desc"

    name = fields.Char(string="Claim Number", required=True, readonly=True, copy=False, default="New")
    partner_id = fields.Many2one("res.partner", string="Customer", required=True)
    date = fields.Date(string="Date", default=fields.Date.context_today)
    note = fields.Text(string="Internal Note")
    line_ids = fields.One2many("claim.report.line", "claim_id", string="Claim Lines")
    state = fields.Selection([
        ("pending", "Pending"),
        ("register", "Registered"),
        ("sent", "Sent for Claim"),
        ("pass", "Pass"),
        ("fail", "Failed"),
    ], default="pending", string="Status")
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True
    )


    def action_cancel(self):
        self.write({"state": "fail"})

    def action_done(self):
        self.write({"state": "pass"})

    def action_register(self):
        self.write({"state": "register"})

    def action_sent(self):
        self.write({"state": "sent"})

    def action_print_report(self):
        return self.env.ref("aos_claim_aretx.action_report_claim_report").report_action(self)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:

            # detect company
            company_id = vals.get("company_id", self.env.company.id)
            vals["company_id"] = company_id

            # generate sequence
            if vals.get("name", "New") == "New":
                seq = self.env["ir.sequence"].with_context(
                    force_company=company_id
                ).next_by_code("claim.report")
                vals["name"] = seq or "New"

        return super().create(vals_list)

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         if vals.get("name", "New") == "New":
    #             vals["name"] = self.env["ir.sequence"].next_by_code("claim.report") or "New"
    #     return super().create(vals_list)


class ClaimReportLine(models.Model):
    _name = "claim.report.line"
    _description = "Claim Report Line"

    claim_id = fields.Many2one("claim.report", string="Claim Report", ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Product", required=True)
    description = fields.Char(string="Description")
    qty = fields.Float(string="Quantity", default=1.0)
    product_state = fields.Selection([
        ('pending', 'Pending'),
        ('old_received', 'Old Product Received'),
        ('new_received', 'New Product Received'),
        ('closed', 'Closed'),
    ], string='Product State', default='pending', tracking=True)
