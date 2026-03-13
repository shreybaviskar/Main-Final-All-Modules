from odoo import models, fields, api
from odoo.exceptions import UserError


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
        StockQuant = self.env['stock.quant']

        stock_location = self.env.ref('stock.stock_location_stock')

        for rec in self:

            parent_product = rec.product_id
            parent_template = parent_product.product_tmpl_id
            parent_length = parent_template.length

            if parent_product.qty_available <= 0:
                raise UserError("No stock available for the parent product.")

            total_cut = sum(line.length * line.quantity for line in rec.line_ids)

            if total_cut > parent_length:
                raise UserError("Cut length exceeds parent product length.")

            remaining_length = parent_length - total_cut

            # ------------------------------------------------
            # Reduce Parent Log Stock
            # ------------------------------------------------

            parent_quant = StockQuant.search([
                ('product_id', '=', parent_product.id),
                ('location_id', '=', stock_location.id)
            ], limit=1)

            if not parent_quant:
                raise UserError("Parent product stock not found in WH/Stock.")

            parent_quant.inventory_quantity = parent_quant.quantity - 1
            parent_quant.action_apply_inventory()

            # ------------------------------------------------
            # Create Child Pieces
            # ------------------------------------------------

            for line in rec.line_ids:

                child_name = f"{parent_product.name} {line.length}m"

                product = ProductTemplate.search([
                    ('name', '=', child_name),
                    ('length', '=', line.length),
                    ('is_parent', '=', False)
                ], limit=1)

                if not product:
                    product = ProductTemplate.create({
                        'name': child_name,
                        'length': line.length,
                        'is_parent': False,
                        'uom_id': parent_template.uom_id.id,
                        'is_storable': True,
                    })

                product_variant = product.product_variant_id

                quant = StockQuant.search([
                    ('product_id', '=', product_variant.id),
                    ('location_id', '=', stock_location.id)
                ], limit=1)

                if quant:
                    quant.inventory_quantity = quant.quantity + line.quantity
                else:
                    quant = StockQuant.create({
                        'product_id': product_variant.id,
                        'location_id': stock_location.id,
                        'inventory_quantity': line.quantity,
                    })

                quant.action_apply_inventory()

            # ------------------------------------------------
            # Remaining Piece
            # ------------------------------------------------

            if remaining_length > 0:

                remain_name = f"{parent_product.name} {remaining_length}m"

                remain_product = ProductTemplate.search([
                    ('name', '=', remain_name),
                    ('length', '=', remaining_length),
                    ('is_parent', '=', False)
                ], limit=1)

                if not remain_product:
                    remain_product = ProductTemplate.create({
                        'name': remain_name,
                        'length': remaining_length,
                        'is_parent': False,
                        'uom_id': parent_template.uom_id.id,
                        'is_storable': True,
                    })

                remain_variant = remain_product.product_variant_id

                quant = StockQuant.search([
                    ('product_id', '=', remain_variant.id),
                    ('location_id', '=', stock_location.id)
                ], limit=1)

                if quant:
                    quant.inventory_quantity = quant.quantity + 1
                else:
                    quant = StockQuant.create({
                        'product_id': remain_variant.id,
                        'location_id': stock_location.id,
                        'inventory_quantity': 1,
                    })

                quant.action_apply_inventory()