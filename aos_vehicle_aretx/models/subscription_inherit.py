from odoo import api, fields, models


class CustomSubscriptionPackage(models.Model):
    _inherit = "subscription.package"

    vehicle_number_sub = fields.Many2one('vehicle.mapper.master.model', string='Vehicle number',domain="[('x_customer_id','=',partner_id)]")
