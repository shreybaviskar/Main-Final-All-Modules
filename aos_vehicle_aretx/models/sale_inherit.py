from odoo import api, fields, models


class CustomSale(models.Model):
    _inherit = "sale.order"

    x_vehicle_number_id = (fields.Many2one('vehicle.master.model',
                                          string='Vehicle number',
                                          domain="[('x_customer_id','=',partner_id)]"))
    vehicle_kms = fields.Char(string='Vehicle KMS')

    vehicle_brand_model = fields.Char(
        string="Vehicle (Brand - Model)",
        related="x_vehicle_number_id.display_brand_model",
        store=True
    )

    def _prepare_invoice(self):
        invoice_vals=super(CustomSale, self)._prepare_invoice()
        invoice_vals['vehicle_number']=self.x_vehicle_number_id.id
        print("invoice vals",invoice_vals)
        return invoice_vals
