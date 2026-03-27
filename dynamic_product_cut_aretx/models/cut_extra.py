from odoo import models, fields


class DynamicCutAvailability(models.Model):
    _name = 'dynamic.cut.availability'
    _description = 'Cut Availability'

    cut_id = fields.Many2one('dynamic.product.cut', ondelete='cascade')
    product_id = fields.Many2one('product.product')

    required_qty = fields.Float()
    available_qty = fields.Float()

    is_available = fields.Boolean()


class DynamicCutResult(models.Model):
    _name = 'dynamic.cut.result'
    _description = 'Cut Result'
    _order = 'source_product_id, id'  # Group by source log visually

    cut_id = fields.Many2one('dynamic.product.cut', ondelete='cascade')

    source_product_id = fields.Many2one('product.product', string="Source Log")
    product_id = fields.Many2one('product.product', string="Cut Piece")
    quantity = fields.Float()