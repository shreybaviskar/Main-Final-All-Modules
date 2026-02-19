from odoo import api, fields, models


class CustomInvoice(models.Model):
    _inherit = "account.move"

    vehicle_kms = fields.Char(string='Vehicle KMS')

    vehicle_number = fields.Many2one(
        'vehicle.master.model',
        string='Vehicle Number',
        domain="[('x_customer_id', '=', partner_id)]"
    )

    vehicle_brand_model = fields.Char(
        string="Vehicle (Brand - Model)",
        related="vehicle_number.display_brand_model",
        store=True,
        readonly=True
    )

