# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_service_combo = fields.Boolean(
        string='Is Service Combo',
        default=False
    )

    contract_duration = fields.Integer(
        string='Contract Duration In Months'
    )


    x_service_combo_ids = fields.One2many(
        'service.combo.item',
        'service_combo_id',
        string="Service Combo Items"
    )


    # x_service_ids = fields.One2many('service.combo.item', 'service_id', string="Service")
    # x_quantity_ids = fields.One2many('service.combo.item', 'no_of_items', string="Quantity")

    @api.onchange('is_service_combo')
    def onchange_is_service_combo(self):
        """Clear combo items when unchecked"""
        if not self.is_service_combo:
            self.x_service_combo_ids = [(5, 0, 0)]

    @api.onchange('type')
    def onchange_type(self):
        """Clear combo checkbox if type is not service"""
        if self.type != 'service':
            self.is_service_combo = False
            self.x_service_combo_ids = [(5, 0, 0)]