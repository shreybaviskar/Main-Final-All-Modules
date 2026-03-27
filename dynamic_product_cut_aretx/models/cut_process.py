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
        'cut_id'
    )

    cut_result_ids = fields.One2many(
        'dynamic.cut.result',
        'cut_id'
    )

    def action_process_cut(self):

        ProductTemplate = self.env['product.template']
        StockQuant = self.env['stock.quant']
        stock_location = self.env.ref('stock.stock_location_stock')

        for rec in self:

            if not rec.line_ids:
                raise UserError("Please add cut lines.")

            # -----------------------------
            # CLEAR OLD DATA
            # -----------------------------
            rec.availability_ids.unlink()
            rec.cut_result_ids.unlink()

            code = rec.wood_template_id.default_code
            prefix = '-'.join(code.split('-')[:2])  # e.g. nw-10

            width = rec.wood_template_id.width

            # -----------------------------
            # STEP 1: AGGREGATE REQUIREMENTS
            # -----------------------------
            length_counter = {}
            for line in rec.line_ids:
                length_counter[line.length] = length_counter.get(line.length, 0) + line.quantity

            remaining_lengths = []

            # -----------------------------
            # STEP 2: CHECK STOCK (NO DEDUCTION)
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

                if available_qty < required_qty:
                    shortage = int(required_qty - available_qty)
                    remaining_lengths.extend([length] * shortage)

            # -----------------------------
            # STEP 3: NOTHING TO CUT
            # -----------------------------
            if not remaining_lengths:
                return

            # Lengths that are in shortage — never use as source logs
            shortage_lengths = set(remaining_lengths)

            # -----------------------------
            # STEP 4: BUILD LOG POOL
            # Rules per length in the same wood family:
            #   • In shortage                → exclude entirely (we need those pieces, can't cut them)
            #   • In order but fully stocked → reserve the ordered qty, pool only the SURPLUS units
            #   • Not in order at all        → pool all available units
            #
            # This ensures we never consume stock committed to an order line,
            # while still allowing surplus units of ordered lengths to be
            # used as source logs for other cuts.
            # -----------------------------
            candidates = ProductTemplate.search([
                ('default_code', 'like', f'{prefix}-%'),
                ('length', 'not in', list(shortage_lengths)),
            ])

            log_pool = []
            for product in candidates:
                quant = StockQuant.search([
                    ('product_id', '=', product.product_variant_id.id),
                    ('location_id', '=', stock_location.id),
                    ('quantity', '>', 0)
                ], limit=1)

                if not quant:
                    continue

                available = int(quant.quantity)

                # Reserve units already committed to this order length
                # (shortage lengths excluded above, so this only applies to
                #  fully-stocked ordered lengths like 100m ordered x2, stock x95)
                reserved = int(length_counter.get(product.length, 0))

                # Only pool the surplus beyond what the order already covers
                usable = available - reserved
                if usable <= 0:
                    continue

                for _ in range(usable):
                    log_pool.append({
                        'product': product,
                        'length': product.length,
                        'used': False,
                    })

            # Sort pool: shortest logs first → prefer smaller logs to minimise waste
            log_pool.sort(key=lambda x: x['length'])

            # -----------------------------
            # STEP 5: FIRST FIT DECREASING (FFD) BIN PACKING
            # Process pieces largest-first so bigger cuts get placed first.
            # Try to fill already-opened logs before opening a new one.
            # -----------------------------
            bins = []
            # bin structure: {
            #   'log_entry': pool entry,
            #   'product': product.template,
            #   'log_length': float,
            #   'remaining': float,
            #   'pieces': [float, ...]
            # }

            for piece in sorted(remaining_lengths, reverse=True):

                placed = False

                # Try fitting into an already-open bin (best use of opened logs)
                for b in bins:
                    if b['remaining'] >= piece:
                        b['pieces'].append(piece)
                        b['remaining'] -= piece
                        placed = True
                        break

                if not placed:
                    # Open the smallest unused log that can fit this piece
                    for log_entry in log_pool:
                        if not log_entry['used'] and log_entry['length'] >= piece:
                            log_entry['used'] = True
                            bins.append({
                                'log_entry': log_entry,
                                'product': log_entry['product'],
                                'log_length': log_entry['length'],
                                'remaining': log_entry['length'] - piece,
                                'pieces': [piece],
                            })
                            placed = True
                            break

                if not placed:
                    raise UserError(
                        f"No log available to cut a piece of {piece}m. "
                        f"Please ensure a log longer than {piece}m is in stock."
                    )

            # -----------------------------
            # STEP 6: PROCESS EACH BIN
            # For every log used: deduct stock, create cut pieces,
            # put back the leftover piece.
            # -----------------------------
            for b in bins:

                source_product = b['product']
                parent_variant = source_product.product_variant_id

                # --- Deduct 1 unit from source log ---
                parent_quant = StockQuant.search([
                    ('product_id', '=', parent_variant.id),
                    ('location_id', '=', stock_location.id)
                ], limit=1)

                if not parent_quant or parent_quant.quantity <= 0:
                    raise UserError(
                        f"Log '{source_product.name}' ran out of stock during processing."
                    )

                parent_quant.inventory_quantity = parent_quant.quantity - 1
                parent_quant.action_apply_inventory()

                # --- Create child cut pieces ---
                for length in b['pieces']:

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

                    rec.cut_result_ids.create({
                        'cut_id': rec.id,
                        'product_id': variant.id,
                        'quantity': 1,
                        'source_product_id': parent_variant.id,
                    })

                # --- Handle leftover piece from this log ---
                remaining_piece = b['remaining']

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
                            'is_storable': True,
                        })

                    variant = remain_product.product_variant_id

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