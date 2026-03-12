from odoo import models, fields

class DynamicProductCutLine(models.Model):
    _name = 'dynamic.product.cut.line'
    _description = 'Dynamic Product Cut Line'

    cut_id = fields.Many2one(
        'dynamic.product.cut',
        string="Cut",
        ondelete='cascade'
    )

    name = fields.Char(string="Description")

    length = fields.Float(string="Length")

    quantity = fields.Integer(string="Quantity")