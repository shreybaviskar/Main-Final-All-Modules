from odoo import models, fields


class DynamicProductCutLine(models.Model):
    _name = 'dynamic.product.cut.line'
    _description = 'Dynamic Product Cut Line'

    cut_id = fields.Many2one(
        'dynamic.product.cut',
        string="Cut Process",
        ondelete='cascade'
    )

    length = fields.Float(string="Length (mtr)", required=True)
    quantity = fields.Integer(string="Quantity", required=True)