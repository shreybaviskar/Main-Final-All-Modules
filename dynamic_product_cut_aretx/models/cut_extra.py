from odoo import models, fields


class DynamicCutAvailability(models.Model):
    _name = 'dynamic.cut.availability'
    _description = 'Cut Availability'

    cut_id = fields.Many2one('dynamic.product.cut', ondelete='cascade')

    # Existing product if it already exists in stock
    product_id = fields.Many2one('product.product', string="Product")

    # Always stored — shows expected code even when product doesn't exist yet
    # e.g. "nw-10-51" for a 51m piece that has never been cut before
    expected_code = fields.Char(string="Expected Code")

    # Length stored separately so the label never goes blank
    length = fields.Float(string="Length (mtr)")

    required_qty = fields.Float(string="Required Qty")
    available_qty = fields.Float(string="Available Qty")
    is_available = fields.Boolean(string="Is Available")


class DynamicCutResult(models.Model):
    _name = 'dynamic.cut.result'
    _description = 'Cut Result'
    _order = 'source_product_id, is_offcut, id'

    cut_id = fields.Many2one('dynamic.product.cut', ondelete='cascade')

    source_product_id = fields.Many2one('product.product', string="Source Log")
    product_id = fields.Many2one('product.product', string="Cut Piece")
    quantity = fields.Float(string="Quantity")

    # Length of this specific piece — used for per-group subtotals in the list
    length_cut = fields.Float(string="Length (mtr)", digits=(12, 2))

    # True for the leftover remainder piece — shown differently in the view
    is_offcut = fields.Boolean(string="Offcut / Remainder", default=False)