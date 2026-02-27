# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    visible_on_pinvoice = fields.Boolean(
        string='Visible on Print Invoice',
        default=False,
        help='If checked, this service will be shown in the print invoice report'
    )