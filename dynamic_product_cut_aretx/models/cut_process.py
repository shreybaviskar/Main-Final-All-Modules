from odoo import models, fields


class DynamicProductCut(models.Model):
    _name = 'dynamic.product.cut'
    _description = 'Dynamic Product Cutting'

    name = fields.Char(default="Cut Process")

    product_id = fields.Many2one(
        'product.product',
        string="Parent Product",
        domain=[('product_tmpl_id.is_parent', '=', True)],
        required=True
    )

    line_ids = fields.One2many(
        'dynamic.product.cut.line',
        'cut_id',
        string="Cut Lines"
    )

    def action_process_cut(self):

        ProductTemplate = self.env['product.template']
        location = self.env.ref('stock.stock_location_stock')

        for rec in self:

            parent_product = rec.product_id
            parent_template = parent_product.product_tmpl_id

            for line in rec.line_ids:

                child_name = f"{parent_product.name} {line.length}m"

                existing_product = ProductTemplate.search([
                    ('name', '=', child_name),
                    ('length', '=', line.length),
                    ('is_parent', '=', False)
                ], limit=1)

                if not existing_product:
                    product = ProductTemplate.create({
                        'name': child_name,
                        'length': line.length,
                        'is_parent': False,
                        'uom_id': parent_template.uom_id.id,
                        'is_storable': True,
                    })

                    # create stock quantity
                    self.env['stock.quant']._update_available_quantity(
                        product.product_variant_id,
                        location,
                        line.quantity
                    )