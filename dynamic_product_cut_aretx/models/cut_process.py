from odoo import models, fields, api
from odoo.exceptions import UserError


class DynamicProductCut(models.Model):
    _name = 'dynamic.product.cut'
    _description = 'Dynamic Product Cutting'

    name = fields.Char(default="Cut Process")

    wood_template_id = fields.Many2one(
        'product.template',
        string="Wood Type",
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

            if not rec.line_ids:
                raise UserError("Please add cut lines.")

            width = rec.wood_template_id.width

            # PREPARE CUT REQUIREMETS

            required_lengths = []

            for line in rec.line_ids:
                for i in range(line.quantity):
                    required_lengths.append(line.length)

            remaining_lengths = []

            # STEP 1 : CHECK EXACT LOGS

            for length in required_lengths:

                product = ProductTemplate.search([
                    ('name', 'ilike', rec.wood_template_id.name),
                    ('length', '=', length),
                ], limit=1)

                if not product:
                    remaining_lengths.append(length)
                    continue

                quant = StockQuant.search([
                    ('product_id', '=', product.product_variant_id.id),
                    ('location_id', '=', stock_location.id),
                    ('quantity', '>', 0)
                ], limit=1)

                if quant:
                    quant.inventory_quantity = quant.quantity - 1
                    quant.action_apply_inventory()
                else:
                    remaining_lengths.append(length)

            # STEP 2 : SUM REMAINING CUTS

            remaining_total = sum(remaining_lengths)

            if remaining_total == 0:
                return

            # STEP 3 : FIND BEST LOG

            candidates = ProductTemplate.search([
                ('name', 'ilike', rec.wood_template_id.name)
            ])

            best_product = None
            best_length = None

            for product in candidates:

                length = product.length

                quant = StockQuant.search([
                    ('product_id', '=', product.product_variant_id.id),
                    ('location_id', '=', stock_location.id),
                    ('quantity', '>', 0)
                ], limit=1)

                if not quant:
                    continue

                if length >= remaining_total:

                    if not best_length or length < best_length:
                        best_product = product
                        best_length = length

            if not best_product:
                raise UserError("No suitable wood log available in stock")

            parent_variant = best_product.product_variant_id

            parent_quant = StockQuant.search([
                ('product_id', '=', parent_variant.id),
                ('location_id', '=', stock_location.id)
            ], limit=1)

            parent_quant.inventory_quantity = parent_quant.quantity - 1
            parent_quant.action_apply_inventory()

            remaining_piece = best_length - remaining_total

            # CREATE CUT PRODUCTS

            for length in remaining_lengths:

                child_code = f"nw-{int(width)}-{int(length)}"

                product = ProductTemplate.search([
                    ('default_code', '=', child_code)
                ], limit=1)

                if not product:
                    product = ProductTemplate.create({
                        'name': f"{rec.wood_template_id.name} {length}m",
                        'default_code': child_code,
                        'width': width,
                        'length': length,
                        'uom_id': rec.wood_template_id.uom_id.id,
                        'is_storable': True,
                    })

                variant = product.product_variant_id

                quant = StockQuant.search([
                    ('product_id', '=', variant.id),
                    ('location_id', '=', stock_location.id)
                ], limit=1)

                if quant:
                    quant.inventory_quantity = quant.quantity + 1
                else:
                    quant = StockQuant.create({
                        'product_id': variant.id,
                        'location_id': stock_location.id,
                        'inventory_quantity': 1,
                    })

                quant.action_apply_inventory()

            # CREATE REMAINING PIECE

            if remaining_piece > 0:

                remain_code = f"nw-{int(width)}-{int(remaining_piece)}"

                remain_product = ProductTemplate.search([
                    ('default_code', '=', remain_code)
                ], limit=1)

                if not remain_product:
                    remain_product = ProductTemplate.create({
                        'name': f"{rec.wood_template_id.name} {remaining_piece}m",
                        'default_code': remain_code,
                        'width': width,
                        'length': remaining_piece,
                        'uom_id': rec.wood_template_id.uom_id.id,
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