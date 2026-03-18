from odoo import models, fields
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

    availability_ids = fields.One2many(
        'dynamic.cut.availability',
        'cut_id',
        string="Availability"
    )

    cut_result_ids = fields.One2many(
        'dynamic.cut.result',
        'cut_id',
        string="Cut Results"
    )

    def action_process_cut(self):

        ProductTemplate = self.env['product.template']
        StockQuant = self.env['stock.quant']
        stock_location = self.env.ref('stock.stock_location_stock')

        for rec in self:

            if not rec.line_ids:
                raise UserError("Please add cut lines.")

            # CLEAR OLD DATA
            rec.availability_ids.unlink()
            rec.cut_result_ids.unlink()

            code = rec.wood_template_id.default_code
            prefix = '-'.join(code.split('-')[:2])  # nw-10

            width = rec.wood_template_id.width

            # -----------------------------
            # STEP 1: PREPARE REQUIREMENTS
            # -----------------------------
            length_counter = {}
            for line in rec.line_ids:
                length_counter[line.length] = length_counter.get(line.length, 0) + line.quantity

            remaining_lengths = []

            # -----------------------------
            # STEP 2: CHECK EXISTING STOCK (NO DEDUCTION)
            # -----------------------------
            for length, required_qty in length_counter.items():

                product = ProductTemplate.search([
                    ('default_code', 'like', f'{prefix}-%'),
                    ('length', '=', length),
                ], limit=1)

                available_qty = 0

                if product:
                    quant = StockQuant.search([
                        ('product_id', '=', product.product_variant_id.id),
                        ('location_id', '=', stock_location.id),
                    ], limit=1)

                    if quant:
                        available_qty = quant.quantity

                # LOG AVAILABILITY
                rec.availability_ids.create({
                    'cut_id': rec.id,
                    'product_id': product.product_variant_id.id if product else False,
                    'required_qty': required_qty,
                    'available_qty': available_qty,
                    'is_available': available_qty >= required_qty
                })

                # OLD LOGIC → DO NOT CUT IF AVAILABLE
                if available_qty >= required_qty:
                    continue

                shortage = int(required_qty - available_qty)

                if shortage > 0:
                    remaining_lengths.extend([length] * shortage)

            # -----------------------------
            # STEP 3: IF NOTHING TO CUT → EXIT
            # -----------------------------
            if not remaining_lengths:
                return

            remaining_total = sum(remaining_lengths)

            # -----------------------------
            # STEP 4: FIND BEST LOG
            # -----------------------------
            candidates = ProductTemplate.search([
                ('default_code', 'like', f'{prefix}-%')
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

            # 🔴 ONLY deduct parent log (same as old logic)
            parent_quant.inventory_quantity = parent_quant.quantity - 1
            parent_quant.action_apply_inventory()

            remaining_piece = best_length - remaining_total

            # -----------------------------
            # STEP 5: CREATE CUT PRODUCTS
            # -----------------------------
            for length in remaining_lengths:

                child_code = f"{prefix}-{int(length)}"

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
                        'is_storable': True
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

                # CUT RESULT LOG
                rec.cut_result_ids.create({
                    'cut_id': rec.id,
                    'product_id': variant.id,
                    'quantity': 1,
                    'source_product_id': parent_variant.id
                })

            # -----------------------------
            # STEP 6: REMAINING PIECE
            # -----------------------------
            if remaining_piece > 0:

                remain_code = f"{prefix}-{int(remaining_piece)}"

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
                        'is_storable': True
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