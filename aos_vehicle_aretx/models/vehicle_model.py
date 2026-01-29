# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ModelName(models.Model):
    _name = "vehicle.model.model"
    _description = "Models"

    brand_id = fields.Many2one('vehicle.brand.model', string="Brand Name",ondelete='restrict')
    name = fields.Char(string='Model Name', required=True,ondelete='restrict')
    type_id = fields.Many2one('vehicle.type.model', string="Vehicle Type",ondelete='restrict')






