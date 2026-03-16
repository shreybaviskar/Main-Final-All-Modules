from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    width = fields.Float(
        string="Width (MM)",
        help="Base width used for cutting operations"
    )

    length = fields.Float(
        string="Length (Mtr)",
        help="Base length used for cutting operations"
    )
