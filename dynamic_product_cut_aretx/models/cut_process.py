import io
import base64
from collections import defaultdict

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

            # Count unique (source_product_id, log_index) pairs = physical logs used
            rec.total_logs_used = len(
                set((r.source_product_id.id, r.log_index) for r in results)
            )

            # Total meters taken from stock
            rec.total_length_sourced = sum(results.mapped('length_cut'))

            # Waste = sum of offcut lengths
            offcut_total = sum(r.length_cut for r in results if r.is_offcut)
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

            # CLEAR OLD DATA
            rec.availability_ids.unlink()
            rec.cut_result_ids.unlink()

            code = rec.wood_template_id.default_code
            prefix = '-'.join(code.split('-')[:2])  # e.g. nw-10
            width = rec.wood_template_id.width

            # STEP 1: AGGREGATE REQUIREMENTS
            length_counter = {}
            for line in rec.line_ids:
                length_counter[line.length] = length_counter.get(line.length, 0) + line.quantity

            remaining_lengths = []

            # STEP 2: CHECK STOCK (NO DEDUCTION)
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

            # STEP 3: NOTHING TO CUT
            if not remaining_lengths:
                return

            shortage_lengths = set(remaining_lengths)

            # STEP 4: BUILD LOG POOL
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

            log_pool.sort(key=lambda x: x['length'])

            # STEP 5: BEST FIT DECREASING BIN PACKING
            bins = []

            for piece in sorted(remaining_lengths, reverse=True):

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

            # STEP 6: PROCESS EACH BIN
            # log_index is a 1-based counter so individual physical logs can be
            # distinguished in the Cut Details list and in the downloaded report.
            for log_index, b in enumerate(bins, start=1):

                source_product = b['product']
                parent_variant = source_product.product_variant_id

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
                        'log_index': log_index,
                    })

                # Offcut / remainder piece
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

                    rec.cut_result_ids.create({
                        'cut_id': rec.id,
                        'product_id': variant.id,
                        'quantity': 1,
                        'length_cut': remaining_piece,
                        'source_product_id': parent_variant.id,
                        'is_offcut': True,
                        'log_index': log_index,
                    })

    # ── Download Cut Plan (Excel) ────────────────────────────────────────────

    def action_download_cut_plan(self):
        """
        Generate an Excel workbook showing the cut plan grouped by individual
        physical log (source_product_id + log_index), matching the layout in
        the reference Excel screenshot:

            Source Log  │  Cut Piece Code  │  Length (mtr)  │  Offcut?
            ────────────┼──────────────────┼────────────────┼─────────
            nw-10-100   │  nw-10-51        │  51.00         │
            (merged)    │  nw-10-47        │  47.00         │
                        │  nw-10-2         │   2.00         │  ✓
            nw-10-100   │  nw-10-51        │  51.00         │
            (merged)    │  …               │  …             │
        """
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(
                "The 'xlsxwriter' Python package is required to generate the "
                "Excel report. Ask your system administrator to install it."
            )

        self.ensure_one()

        if not self.cut_result_ids:
            raise UserError("No cut results found. Please run Process first.")

        # ── Workbook / formats ───────────────────────────────────────────────
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Cut Plan')

        # Base formats
        bold = wb.add_format({'bold': True})

        title_fmt = wb.add_format({
            'bold': True, 'font_size': 14, 'font_color': '#1F3864',
        })
        subtitle_fmt = wb.add_format({
            'italic': True, 'font_color': '#595959', 'font_size': 10,
        })

        col_header_fmt = wb.add_format({
            'bold': True, 'bg_color': '#1F3864', 'font_color': '#FFFFFF',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'text_wrap': True,
        })

        log_fmt = wb.add_format({
            'bold': True, 'bg_color': '#D6E4F0', 'font_color': '#1F3864',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'text_wrap': True,
        })

        piece_fmt = wb.add_format({
            'border': 1, 'align': 'left', 'valign': 'vcenter',
        })
        piece_num_fmt = wb.add_format({
            'border': 1, 'align': 'right', 'valign': 'vcenter',
            'num_format': '0.00',
        })

        offcut_label_fmt = wb.add_format({
            'border': 1, 'align': 'left', 'valign': 'vcenter',
            'italic': True, 'font_color': '#888888', 'bg_color': '#F5F5F5',
        })
        offcut_num_fmt = wb.add_format({
            'border': 1, 'align': 'right', 'valign': 'vcenter',
            'num_format': '0.00', 'italic': True,
            'font_color': '#888888', 'bg_color': '#F5F5F5',
        })
        offcut_tick_fmt = wb.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'italic': True, 'font_color': '#888888', 'bg_color': '#F5F5F5',
            'bold': True,
        })

        summary_label_fmt = wb.add_format({
            'bold': True, 'bg_color': '#EBF1DE', 'border': 1,
            'align': 'right', 'valign': 'vcenter',
        })
        summary_val_fmt = wb.add_format({
            'bold': True, 'bg_color': '#EBF1DE', 'border': 1,
            'num_format': '0.00', 'align': 'right',
        })
        summary_pct_fmt = wb.add_format({
            'bold': True, 'bg_color': '#EBF1DE', 'border': 1,
            'num_format': '0.0"%"', 'align': 'right',
        })

        # ── Column widths ────────────────────────────────────────────────────
        ws.set_column(0, 0, 24)   # A – Source Log
        ws.set_column(1, 1, 28)   # B – Cut Piece
        ws.set_column(2, 2, 14)   # C – Length (mtr)
        ws.set_column(3, 3, 8)    # D – Qty
        ws.set_column(4, 4, 9)    # E – Offcut?

        # ── Title block ──────────────────────────────────────────────────────
        row = 0
        ws.write(row, 0, 'CUT PLAN REPORT', title_fmt)
        row += 1
        ws.write(row, 0, f'Process : {self.name}', subtitle_fmt)
        row += 1
        ws.write(row, 0, f'Wood Type: {self.wood_template_id.display_name}', subtitle_fmt)
        row += 2   # blank row

        # ── Column headers ───────────────────────────────────────────────────
        ws.set_row(row, 22)
        ws.write(row, 0, 'Source Log',    col_header_fmt)
        ws.write(row, 1, 'Cut Piece',     col_header_fmt)
        ws.write(row, 2, 'Length (mtr)',  col_header_fmt)
        ws.write(row, 3, 'Qty',           col_header_fmt)
        ws.write(row, 4, 'Offcut',        col_header_fmt)
        row += 1

        # Thin separator row drawn between log groups
        sep_fmt = wb.add_format({
            'bg_color': '#FFFFFF', 'top': 2, 'top_color': '#1F3864',
        })

        # ── Group results by (log_index, source_product_id) ──────────────────
        # Each unique (log_index, source_product_id) pair = one physical log.
        # Two logs of the same product get different log_index values (1, 2, …)
        # and therefore appear as completely separate groups in the report.
        groups = defaultdict(list)
        for r in self.cut_result_ids.sorted(
            lambda x: (x.log_index, x.source_product_id.id, x.is_offcut, x.id)
        ):
            groups[(r.log_index, r.source_product_id.id)].append(r)

        # Keep groups in original processing order (by log_index)
        ordered_keys = sorted(groups.keys(), key=lambda k: k[0])

        for group_num, key in enumerate(ordered_keys, start=1):
            log_idx, _src_id = key
            results  = groups[key]
            source   = results[0].source_product_id
            group_start = row

            # Write each piece row
            for r in results:
                if r.is_offcut:
                    lbl_fmt = offcut_label_fmt
                    num_fmt = offcut_num_fmt
                    tick    = '✓'
                else:
                    lbl_fmt = piece_fmt
                    num_fmt = piece_num_fmt
                    tick    = ''

                ws.write(row, 1, r.product_id.display_name, lbl_fmt)
                ws.write(row, 2, r.length_cut,              num_fmt)
                ws.write(row, 3, int(r.quantity),           lbl_fmt)
                ws.write(row, 4, tick,
                         offcut_tick_fmt if r.is_offcut else piece_fmt)
                ws.set_row(row, 18)
                row += 1

            # Source log label — includes Log #N so consecutive logs of the
            # same product are always visually distinct merged cells.
            group_end = row - 1
            log_label = (
                f"Log #{log_idx}\n"
                f"{source.display_name}\n"
                f"({source.product_tmpl_id.length:.0f}m)"
            )
            if group_end > group_start:
                ws.merge_range(group_start, 0, group_end, 0,
                               log_label, log_fmt)
            else:
                ws.write(group_start, 0, log_label, log_fmt)

            # Thin separator row between log groups (skip after last group)
            if group_num < len(ordered_keys):
                ws.set_row(row, 5)
                for col in range(5):
                    ws.write(row, col, '', sep_fmt)
                row += 1

        # ── Summary block ────────────────────────────────────────────────────
        row += 1
        ws.write(row, 2, 'Total Required (mtr)', summary_label_fmt)
        ws.write(row, 3, self.total_length_required, summary_val_fmt)
        row += 1
        ws.write(row, 2, 'Total Sourced (mtr)',   summary_label_fmt)
        ws.write(row, 3, self.total_length_sourced, summary_val_fmt)
        row += 1
        ws.write(row, 2, 'Total Waste (mtr)',     summary_label_fmt)
        ws.write(row, 3, self.total_waste,         summary_val_fmt)
        row += 1
        ws.write(row, 2, 'Efficiency (%)',        summary_label_fmt)
        ws.write(row, 3, self.efficiency_pct,      summary_pct_fmt)

        # ── Freeze top rows ──────────────────────────────────────────────────
        ws.freeze_panes(5, 0)   # freeze title + header

        wb.close()
        xlsx_data = output.getvalue()

        # Save as attachment so the browser can download it
        attachment = self.env['ir.attachment'].create({
            'name': f'cut_plan_{self.name.replace(" ", "_")}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(xlsx_data).decode(),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': (
                'application/vnd.openxmlformats-officedocument'
                '.spreadsheetml.sheet'
            ),
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }