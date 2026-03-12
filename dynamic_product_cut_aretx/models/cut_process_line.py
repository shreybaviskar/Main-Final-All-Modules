from odoo import models, fields, api


class DynamicProductCutLine(models.Model):
    _name = 'dynamic.product.cut.line'
    _description = 'Dynamic Product Cut Line'

    cut_id = fields.Many2one(
        'dynamic.product.cut',
        string="Cut",
        ondelete='cascade'
    )

    name = fields.Char(
        string="Description",
        compute="_compute_name",
        store=True
    )

    length = fields.Float(string="Length")
    quantity = fields.Integer(string="Quantity")

    @api.depends('length', 'quantity', 'cut_id.product_id')
    def _compute_name(self):
        for rec in self:
            if rec.cut_id.product_id:
                rec.name = f"{rec.cut_id.product_id.name} {rec.length}mtr - {rec.quantity} qty"