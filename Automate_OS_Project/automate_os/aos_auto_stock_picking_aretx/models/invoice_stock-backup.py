from odoo.exceptions import UserError
from odoo import models, fields, api, _
from odoo.tools.misc import OrderedSet


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _create_stock_moves(self, picking):
        """Create stock moves for invoice lines"""
        moves = self.env['stock.move']

        for line in self:
            # Skip if no product or not a stockable/consumable product
            if not line.product_id or line.product_id.type not in ('product', 'consu'):
                continue

            # Skip if quantity is zero or negative
            if line.quantity <= 0:
                continue

            # Determine source and destination locations based on invoice type
            picking_type = picking.picking_type_id

            if line.move_id.move_type == 'out_invoice':
                # Customer Invoice: Stock -> Customer
                location_id = picking_type.default_location_src_id.id or picking.location_id.id
                location_dest_id = picking_type.default_location_dest_id.id or picking.location_dest_id.id
            elif line.move_id.move_type == 'in_invoice':
                # Vendor Bill: Supplier -> Stock
                location_id = picking_type.default_location_src_id.id or picking.location_id.id
                location_dest_id = picking_type.default_location_dest_id.id or picking.location_dest_id.id
            else:
                continue

            # Create the stock move
            move_vals = {
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'picking_id': picking.id,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'origin': line.move_id.name,
                'company_id': line.company_id.id,
            }

            move = self.env['stock.move'].create(move_vals)
            moves |= move

        # Confirm the moves if any were created
        if moves:
            moves._action_confirm()

        return moves


class InvoiceStockMove(models.Model):
    _inherit = 'account.move'

    def _get_stock_type_ids(self):
        data = self.env['stock.picking.type'].search([])
        if self._context.get('default_move_type') == 'out_invoice':
            return data.filtered(lambda x: x.code == 'outgoing')[:1]
        if self._context.get('default_move_type') == 'in_invoice':
            return data.filtered(lambda x: x.code == 'incoming')[:1]

    # warranty_number = fields.Char(string="Warranty Number")
    picking_count = fields.Integer(string="Count", copy=False)
    invoice_picking_id = fields.Many2one('stock.picking', string="Picking", copy=False)

    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Picking Type',
        default=_get_stock_type_ids,
        readonly=True
    )

    def action_stock_move1(self):
        for move in self:
            # Determine picking type based on invoice type
            if move.move_type == 'out_invoice':
                picking_type = self.env['stock.picking.type'].search(
                    [('code', '=', 'outgoing')], limit=1
                )
            elif move.move_type == 'in_invoice':
                picking_type = self.env['stock.picking.type'].search(
                    [('code', '=', 'incoming')], limit=1
                )
            else:
                continue

            if not picking_type:
                raise UserError(_('No picking type found. Please configure your warehouse.'))

            src = picking_type.default_location_src_id or picking_type.warehouse_id.lot_stock_id
            dest = picking_type.default_location_dest_id or picking_type.warehouse_id.lot_stock_id

            if not src or not dest:
                raise UserError(
                    _('Source or destination location not configured for picking type %s') % picking_type.name)

            # Check for existing picking
            existing_picking = self.env['stock.picking'].search([
                ('origin', '=', move.name),
                ('picking_type_id', '=', picking_type.id),
                ('state', '!=', 'cancel')
            ], limit=1)

            if existing_picking:
                move.invoice_picking_id = existing_picking.id
                move.picking_count = 1
                continue

            # Create new picking
            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'partner_id': move.partner_id.id,
                'origin': move.name,
                'location_id': src.id,
                'location_dest_id': dest.id,
                'move_type': 'direct',
            })

            move.invoice_picking_id = picking.id
            move.picking_count = 1

            # Create stock moves for products
            stockable_lines = move.invoice_line_ids.filtered(
                lambda l: l.product_id and l.product_id.type in ('product', 'consu') and l.quantity > 0
            )

            if stockable_lines:
                stockable_lines._create_stock_moves(picking)

    def action_stock_move(self):
        for move in self:

            # -----------------------------
            # 1️⃣ Check Sale Order link
            # -----------------------------
            sale_orders = move.invoice_line_ids.mapped('sale_line_ids.order_id')

            existing_picking = False

            if sale_orders:
                # Get delivery from SO
                existing_picking = self.env['stock.picking'].search([
                    ('sale_id', 'in', sale_orders.ids),
                    ('state', '!=', 'cancel')
                ], limit=1)

            # -----------------------------
            # 2️⃣ If delivery already exists → USE IT
            # -----------------------------
            if existing_picking:
                move.invoice_picking_id = existing_picking.id
                move.picking_count = 1
                continue

            # -----------------------------
            # 3️⃣ ELSE → Create picking (manual invoice case)
            # -----------------------------
            if move.move_type == 'out_invoice':
                picking_type = self.env['stock.picking.type'].search(
                    [('code', '=', 'outgoing')], limit=1
                )
            elif move.move_type == 'in_invoice':
                picking_type = self.env['stock.picking.type'].search(
                    [('code', '=', 'incoming')], limit=1
                )
            else:
                continue

            if not picking_type:
                raise UserError(_('No picking type found.'))

            src = picking_type.default_location_src_id or picking_type.warehouse_id.lot_stock_id
            dest = picking_type.default_location_dest_id or picking_type.warehouse_id.lot_stock_id

            # Create picking
            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'partner_id': move.partner_id.id,
                'origin': move.name,
                'location_id': src.id,
                'location_dest_id': dest.id,
                'move_type': 'direct',
            })

            move.invoice_picking_id = picking.id
            move.picking_count = 1

            stockable_lines = move.invoice_line_ids.filtered(
                lambda l: l.product_id.type in ('product', 'consu') and l.quantity > 0
            )

            if stockable_lines:
                stockable_lines._create_stock_moves(picking)

    def action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree_ready').read()[0]
        action['domain'] = [('id', '=', self.invoice_picking_id.id)]
        action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
        action['res_id'] = self.invoice_picking_id.id
        return action

    def action_post(self):
        res = super().action_post()
        if self.env.context.get('import_file'):
            return res

        for move in self:
            if move.move_type in ('out_invoice', 'in_invoice'):
                move.action_stock_move()
        return res


# This class is responsible for automatically validating the linked picking when the invoice is posted.

class InvoiceStockMoveValidation(models.Model):
    _inherit = 'account.move'

    def _validate_picking(self, picking):
        """Validate a picking automatically, bypassing wizard popups."""
        if not picking or picking.state == 'done':
            return

        # Step 1: Confirm if still in draft
        if picking.state == 'draft':
            picking.action_confirm()

        # Step 2: Try to reserve stock
        picking.action_assign()

        # Step 3: Force quantity on every move line (Odoo 17+ field names)
        for stock_move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
            stock_move.quantity = stock_move.product_uom_qty
            for move_line in stock_move.move_line_ids:
                move_line.quantity = move_line.quantity or stock_move.product_uom_qty

        # Step 4: Validate — skip_backorder & skip_immediate prevent wizard pop-ups
        picking.with_context(
            skip_backorder=True,
            skip_immediate=True,
        ).button_validate()

    def action_stock_move(self):
        # Run the original logic first (creates/links the picking)
        super().action_stock_move()

        # Now validate whatever picking was linked to each invoice
        for move in self:
            # ✅ FIX: Skip if all invoice lines are service type products
            has_stockable = any(
                l.product_id and l.product_id.type == 'service'
                for l in move.invoice_line_ids
            )
            if has_stockable:
                continue

            if move.invoice_picking_id and move.invoice_picking_id.state != 'done':
                self._validate_picking(move.invoice_picking_id)