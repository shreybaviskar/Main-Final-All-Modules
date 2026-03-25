from odoo import api, fields, models


class VehicleColor(models.Model):
    _name = "vehicle.color.model"

    name = fields.Char(string='Vehicle Color ', required=True,ondelete='restrict')



