from odoo import models, fields,api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    technician_id = fields.Many2one('res.users', string='Technician')

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    
    technician_id_l = fields.Many2one('res.partner', string='Technician',
                                      domain="[('category_id.name', '=', 'Technician')]")


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    product_on_hand = fields.Float(
        string="On Hand Qty",
        compute="_compute_product_on_hand",
        store=False
    )

    @api.depends('product_id')
    def _compute_product_on_hand(self):
        for line in self:
            if line.product_id:
                line.product_on_hand = line.product_id.qty_available
            else:
                line.product_on_hand = 0.0
