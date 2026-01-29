from odoo import api, fields, models

class VehicleType(models.Model):
    _name = "vehicle.type.model"
    _rec_name = "vehicle_type_name"

    vehicle_type_name = fields.Char(string='Vehicle ', required=True,ondelete='restrict')



