from odoo import api, fields, models


class CustomContacts(models.Model):
    _inherit = "res.partner"

    x_brand_ids = fields.Many2many('vehicle.master.model', 'x_brand_id', string="Brand Name",ondelete='restrict')
    x_model_ids = fields.One2many('vehicle.master.model', 'x_model_id', string="Model Name",ondelete='restrict')
    x_vehicle_number_ids = fields.Many2many('vehicle.master.model',string="Brand Name", ondelete='restrict')
    x_color_ids = fields.One2many('vehicle.master.model', 'x_color_id', string="Vehicle Details",ondelete='restrict')

class ResPartner(models.Model):
    _inherit = 'res.partner'

    vehicle_numbers = fields.Char(
        string="Vehicle Numbers",
        compute="_compute_vehicle_numbers",
        store=True,
        index=True,
    )

    @api.depends('x_vehicle_number_ids', 'x_vehicle_number_ids.x_vehicle_number_id')
    def _compute_vehicle_numbers(self):
        for partner in self:
            partner.vehicle_numbers = ', '.join(
                partner.x_vehicle_number_ids.mapped('x_vehicle_number_id')
            )
