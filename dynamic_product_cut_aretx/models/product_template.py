from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    length = fields.Float(
        string="Length (Meters)",
        help="Base length used for cutting operations"
    )

    is_parent = fields.Boolean(
        string="Is Parent Product",
        default=True,
        help="Indicates if this product is a parent product used for cutting"
    )