from odoo import api, fields, models


class CustomContacts(models.Model):
    _inherit = "res.partner"

    x_brand_ids = fields.Many2many('vehicle.master.model', 'x_brand_id', string="Brand Name",ondelete='restrict')
    x_model_ids = fields.One2many('vehicle.master.model', 'x_model_id', string="Model Name",ondelete='restrict')
    x_vehicle_number_ids = fields.Many2many('vehicle.master.model',string="Brand Name", ondelete='restrict')
    x_color_ids = fields.One2many('vehicle.master.model', 'x_color_id', string="Vehicle Details",ondelete='restrict')


