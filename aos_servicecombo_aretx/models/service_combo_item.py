# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ServiceComboItem(models.Model):
    _name = "service.combo.item"
    _description = "Service Combo Item"

    service_combo_id = fields.Many2one(
        'product.template',
        string='Service Combo',
        required=True,
        ondelete='cascade'
    )


    service_id = fields.Many2one(
        'product.template',
        string='Service',
        domain="[('type', '=', 'service'), ('is_service_combo', '=', False)]",
        required=True
    )

    no_of_items = fields.Integer(
        string='Quantity',
        default=1
    )