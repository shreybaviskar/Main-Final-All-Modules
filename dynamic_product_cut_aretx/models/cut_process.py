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

    availability_ids = fields.One2many(
        'dynamic.cut.availability',
        'cut_id'
    )

    cut_result_ids = fields.One2many(
        'dynamic.cut.result',
        'cut_id'
    )

    # ── Summary computed fields ──────────────────────────────────────────────

    total_logs_used = fields.Integer(
        string="Logs Used",
        compute='_compute_summary',
        store=True,
    )

    total_length_required = fields.Float(
        string="Total Required (mtr)",
        compute='_compute_summary',
        store=True,
        digits=(12, 2),
    )

    total_length_sourced = fields.Float(
        string="Total Sourced (mtr)",
        compute='_compute_summary',
        store=True,
        digits=(12, 2),
    )

    total_waste = fields.Float(
        string="Total Waste (mtr)",
        compute='_compute_summary',
        store=True,
        digits=(12, 2),
    )

    efficiency_pct = fields.Float(
        string="Efficiency (%)",
        compute='_compute_summary',
        store=True,
        digits=(5, 1),
    )

    @api.depends(
        'line_ids', 'line_ids.length', 'line_ids.quantity',
        'cut_result_ids', 'cut_result_ids.is_offcut',
        'cut_result_ids.length_cut', 'cut_result_ids.source_product_id',
    )
    def _compute_summary(self):
        for rec in self:
            results = rec.cut_result_ids

            # Total meters requested across all cut lines
            rec.total_length_required = sum(
                l.length * l.quantity for l in rec.line_ids
            )

            # Count unique source logs used
            rec.total_logs_used = len(results.mapped('source_product_id'))

            # Total meters taken from stock (cuts + offcuts = full log lengths used)
            rec.total_length_sourced = sum(results.mapped('length_cut'))

            # Waste = sum of offcut / remainder piece lengths
            offcut_total = sum(
                r.length_cut for r in results if r.is_offcut
            )
            rec.total_waste = offcut_total

            # Efficiency = useful cut meters / total sourced meters
            useful = rec.total_length_sourced - offcut_total
            rec.efficiency_pct = (
                (useful / rec.total_length_sourced * 100)
                if rec.total_length_sourced else 0.0
            )

    # ────────────────────────────────────────────────────────────────────────

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
                # expected_code is always set (e.g. "nw-10-51") so the row label
                # never goes blank even when the product doesn't exist in stock yet.
                rec.availability_ids.create({
                    'cut_id': rec.id,
                    'product_id': product.product_variant_id.id if product else False,
                    'expected_code': f"{prefix}-{int(length)}",
                    'length': length,
                    'required_qty': required_qty,
                    'available_qty': available_qty,
                    'is_available': available_qty >= required_qty,
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
            #   • In shortage                → exclude entirely
            #   • In order but fully stocked → reserve ordered qty, pool only SURPLUS
            #   • Not in order at all        → pool all available units
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
                reserved = int(length_counter.get(product.length, 0))
                usable = available - reserved

                if usable <= 0:
                    continue

                for _ in range(usable):
                    log_pool.append({
                        'product': product,
                        'length': product.length,
                        'used': False,
                    })

            # Sort pool: shortest logs first → minimise waste
            log_pool.sort(key=lambda x: x['length'])

            # -----------------------------
            # STEP 5: BEST FIT DECREASING (BFD) BIN PACKING
            # Pieces sorted largest-first (Decreasing).
            # Each piece goes into the open bin where it fits most tightly
            # (smallest remaining space after placement = Best Fit).
            # This minimises offcut waste vs First Fit.
            # Only opens a new log when no open bin can fit the piece,
            # always picking the smallest available log that fits.
            # -----------------------------
            bins = []

            for piece in sorted(remaining_lengths, reverse=True):

                # Find the open bin with the tightest fit for this piece
                best_bin = None
                best_remaining = None

                for b in bins:
                    leftover = b['remaining'] - piece
                    if leftover >= 0:
                        if best_remaining is None or leftover < best_remaining:
                            best_bin = b
                            best_remaining = leftover

                if best_bin:
                    best_bin['pieces'].append(piece)
                    best_bin['remaining'] -= piece
                else:
                    # No open bin fits — open the smallest unused log that fits
                    new_bin_opened = False
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
                            new_bin_opened = True
                            break

                    if not new_bin_opened:
                        raise UserError(
                            f"No log available to cut a piece of {piece}m. "
                            f"Please ensure a log longer than {piece}m is in stock."
                        )

            # -----------------------------
            # STEP 6: PROCESS EACH BIN
            # -----------------------------
            for b in bins:

                source_product = b['product']
                parent_variant = source_product.product_variant_id

                # Deduct 1 unit from source log
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

                # Create child cut pieces
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
                        'length_cut': length,
                        'source_product_id': parent_variant.id,
                        'is_offcut': False,
                    })

                # Handle leftover / offcut piece
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

                    # Log the offcut in cut results
                    rec.cut_result_ids.create({
                        'cut_id': rec.id,
                        'product_id': variant.id,
                        'quantity': 1,
                        'length_cut': remaining_piece,
                        'source_product_id': parent_variant.id,
                        'is_offcut': True,
                    })