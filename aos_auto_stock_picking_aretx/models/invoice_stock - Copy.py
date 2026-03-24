from odoo.exceptions import UserError
from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet


# import time


class InvoiceStockMove(models.Model):
    _inherit = 'account.move'

    def _get_stock_type_ids(self):
        data = self.env['stock.picking.type'].search([])

        if self._context.get('default_move_type') == 'out_invoice':
            for line in data:
                if line.code == 'outgoing':
                    return line
        if self._context.get('default_move_type') == 'in_invoice':
            for line in data:
                if line.code == 'incoming':
                    return line

    picking_count = fields.Integer(string="Count", copy=False)
    invoice_picking_id = fields.Many2one('stock.picking', string="Picking Id", copy=False)

    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type',
                                      default=_get_stock_type_ids,
                                      help="This will determine picking type of incoming shipment")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('proforma', 'Pro-forma'),
        ('proforma2', 'Pro-forma'),
        ('posted', 'Posted'),
        ('post', 'Post'),
        ('cancel', 'Cancelled'),
        ('done', 'Received'),
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False)

    '''
        This Function will create-update-delete the stock related to invoice actions
    '''

    def action_stock_move(self):

        # print(self.picking_type_id)
        # print('self.picking_type_id')

        # if not self.picking_type_id:
        #     raise UserError(_(" Please select a picking type"))
        for order in self:
            
            if not self.invoice_picking_id:
                pick = {}
                if self.picking_type_id.code == 'outgoing':
                    pick = {
                        'picking_type_id': self.picking_type_id.id,
                        'partner_id': self.partner_id.id,
                        'origin': self.name,
                        'location_dest_id': self.partner_id.property_stock_customer.id,
                        'location_id': self.picking_type_id.default_location_src_id.id,
                        'move_type': 'direct'
                    }
                if self.picking_type_id.code == 'incoming':
                    pick = {
                        'picking_type_id': self.picking_type_id.id,
                        'partner_id': self.partner_id.id,
                        'origin': self.name,
                        'location_dest_id': self.picking_type_id.default_location_dest_id.id,
                        'location_id': self.partner_id.property_stock_supplier.id,
                        'move_type': 'direct'
                    }

                picking = self.env['stock.picking'].create(pick)
                self.invoice_picking_id = picking.id
                self.picking_count = len(picking)
                moves = order.invoice_line_ids.filtered(
                    lambda r: r.product_id.type in ['product', 'consu']).sudo()._create_stock_moves(picking)
                # move_ids = moves.sudo()._action_confirm()
                # move_ids.sudo()._action_assign()
            elif self.invoice_picking_id:
                done = self.env['stock.move'].search([('account_move_id', '=', self.id)])
                for rm in done:
                    # reset on_hand qty
                    # rm.unlink()
                    rm._do_unreserve()
                    rm.unlink()
                    # rm._action_assign()
                moves = order.invoice_line_ids.filtered(
                    lambda r: r.product_id.type in ['product', 'consu']).sudo()._create_stock_moves(
                    self.invoice_picking_id)
                # move_ids = moves._action_confirm()
                # move_ids._action_assign()
                # for item in self.invoice_line_ids:
                #     if item.product_id.id is not False and item.product_id.product_tmpl_id.type is not False and item.product_id.product_tmpl_id.type == 'product':
                #         done = self.env['stock.move'].search([('account_move_line_id', '=', item.id)])
                # if line.

    def action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree_ready')
        result = action.read()[0]
        result.pop('id', None)
        result['context'] = {}
        result['domain'] = [('id', '=', self.invoice_picking_id.id)]
        pick_ids = sum([self.invoice_picking_id.id])
        if pick_ids:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids or False
        return result

    def _reverse_moves(self, default_values_list=None, cancel=False):
        ''' Reverse a recordset of account.move.
        If cancel parameter is true, the reconcilable or liquidity lines
        of each original move will be reconciled with its reverse's.

        :param default_values_list: A list of default values to consider per move.
                                    ('type' & 'reversed_entry_id' are computed in the method).
        :return:                    An account.move recordset, reverse of the current self.
        '''

        if self.picking_type_id.code == 'outgoing':
            data = self.env['stock.picking.type'].search(
                [('company_id', '=', self.company_id.id), ('code', '=', 'incoming')], limit=1)
            self.picking_type_id = data.id
        elif self.picking_type_id.code == 'incoming':
            data = self.env['stock.picking.type'].search(
                [('company_id', '=', self.company_id.id), ('code', '=', 'outgoing')], limit=1)
            self.picking_type_id = data.id
        reverse_moves = super(InvoiceStockMove, self)._reverse_moves()
        return reverse_moves

    def action_post(self):
        # print('you are in inehrit method of confirm invoice..................................')
        res = super(InvoiceStockMove, self).action_post()
        self.action_stock_move()


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done_or_cancel(self):
        for ml in self:
            if ml.state in ('done', 'cancel'):
                if ml.move_id.account_move_id:
                    pass
                else:
                    raise UserError(
                        _('You can not delete product moves if the picking is done. You can only correct the done quantities.'))


class StockMove(models.Model):
    _inherit = 'stock.move'

    account_move_id = fields.Many2one('account.move', String='Account Move')
    account_move_line_id = fields.Many2one('account.move.line', String='Account Move Line')

    def _do_unreserve(self):
        moves_to_unreserve = OrderedSet()
        for move in self:
            if move.state == 'cancel' or (move.state == 'done' and move.scrapped):
                # We may have cancelled move in an open picking in a "propagate_cancel" scenario.
                # We may have done move in an open picking in a scrap scenario.
                continue
            elif move.state == 'done' and not move.account_move_id:
                raise UserError(_("You cannot unreserve a stock move that has been set to 'Done'."))
            moves_to_unreserve.add(move.id)
        moves_to_unreserve = self.env['stock.move'].browse(moves_to_unreserve)

        ml_to_update, ml_to_unlink = OrderedSet(), OrderedSet()
        moves_not_to_recompute = OrderedSet()
        for ml in moves_to_unreserve.move_line_ids:
            if ml.quantity:
                ml_to_update.add(ml.id)
            else:
                ml_to_unlink.add(ml.id)
                moves_not_to_recompute.add(ml.move_id.id)
        ml_to_update, ml_to_unlink = self.env['stock.move.line'].browse(ml_to_update), self.env[
            'stock.move.line'].browse(ml_to_unlink)
        moves_not_to_recompute = self.env['stock.move'].browse(moves_not_to_recompute)
        if ml_to_update.move_id.account_move_id:
            ml_to_update.write({'quantity': 0})
        else:
            ml_to_update.write({'product_uom_qty': 0})
        ml_to_unlink.unlink()
        # `write` on `stock.move.line` doesn't call `_recompute_state` (unlike to `unlink`),
        # so it must be called for each move where no move line has been deleted.
        (moves_to_unreserve - moves_not_to_recompute)._recompute_state()
        return True

    def _check_company_constrains(self):
        """ Override to allow inter-company stock moves """
        return True  # Allow stock moves across different companies

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        if any(move.state not in ('draft', 'cancel') for move in self):
            if self.account_move_id:
                pass
            else:
                raise UserError(_('You can only delete draft moves.'))


class SupplierInvoiceLine(models.Model):
    _inherit = 'account.move.line'

    def _create_stock_moves1(self, picking):
        # print('Mohammad Hsusen', self)
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()

        for line in self:
            price_unit = line.price_unit
            if picking.picking_type_id.code == 'outgoing':
                template = {
                    'name': line.name or '',
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                    'location_id': picking.picking_type_id.default_location_src_id.id,
                    'location_dest_id': line.move_id.partner_id.property_stock_customer.id,
                    'picking_id': picking.id,
                    'account_move_id': line.move_id.id,
                    'account_move_line_id': line.id,
                    'company_id': line.move_id.company_id.id,
                    'picking_type_id': picking.picking_type_id.id,
                    'route_ids': [(6, 0, self.env['stock.location'].search([('id', 'in', (2, 3))]).ids)],
                    'warehouse_id': picking.picking_type_id.warehouse_id.id,
                }
            elif picking.picking_type_id.code == 'incoming':
                template = {
                    'name': line.name or '',
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                    'location_id': line.move_id.partner_id.property_stock_supplier.id,
                    'location_dest_id': picking.picking_type_id.default_location_dest_id.id,
                    'picking_id': picking.id,
                    'account_move_id': line.move_id.id,
                    'account_move_line_id': line.id,
                    'company_id': line.move_id.company_id.id,
                    'picking_type_id': picking.picking_type_id.id,
                    'route_ids': [(6, 0, self.env['stock.location'].search([('id', 'in', (2, 3))]).ids)],
                    'warehouse_id': picking.picking_type_id.warehouse_id.id,
                }

            diff_quantity = line.quantity
            # print('template', template)
            template.update({
                'product_uom_qty': diff_quantity,
                'quantity': diff_quantity,
            })

            # Create move and confirm it instead of setting `state: 'done'`
            move = moves.create(template)
            move._action_confirm()
            move._action_assign()
            move._set_quantity_done(diff_quantity)
            move._action_done()

            done += move

        return done

    def _create_stock_moves(self, picking):
        # print('Mohammad Hsusen', self)
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            price_unit = line.price_unit
            if picking.picking_type_id.code == 'outgoing':
                template = {
                    'name': line.name or '',
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                    'location_id': picking.picking_type_id.default_location_src_id.id,
                    'location_dest_id': line.move_id.partner_id.property_stock_customer.id,
                    'picking_id': picking.id,
                    'account_move_id': line.move_id.id,
                    'account_move_line_id': line.id,
                    'state': 'done',
                    'company_id': line.move_id.company_id.id,
                    'price_unit': price_unit,
                    'picking_type_id': picking.picking_type_id.id,
                    'route_ids': 1 and [
                        (6, 0, [x.id for x in self.env['stock.location'].search([('id', 'in', (2, 3))])])] or [],
                    'warehouse_id': picking.picking_type_id.warehouse_id.id,
                }
            if picking.picking_type_id.code == 'incoming':
                template = {
                    'name': line.name or '',
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                    'location_id': line.move_id.partner_id.property_stock_supplier.id,
                    'location_dest_id': picking.picking_type_id.default_location_dest_id.id,
                    'picking_id': picking.id,
                    'account_move_id': line.move_id.id,
                    'account_move_line_id': line.id,
                    'state': 'done',
                    'company_id': line.move_id.company_id.id,
                    'price_unit': price_unit,
                    'picking_type_id': picking.picking_type_id.id,
                    'route_ids': 1 and [
                        (6, 0, [x.id for x in self.env['stock.location'].search([('id', 'in', (2, 3))])])] or [],
                    'warehouse_id': picking.picking_type_id.warehouse_id.id,
                }
            diff_quantity = line.quantity
            tmp = template.copy()
            tmp.update({
                'product_uom_qty': diff_quantity,
                'quantity': diff_quantity,
            })
            template['product_uom_qty'] = diff_quantity
            template['quantity'] = diff_quantity

            done += moves.create(template)
        return done


# class StockPicking(models.Model):
#     _inherit = 'stock.picking'

#     location_id = fields.Many2one(
#         'stock.location',
#         string="Source Location",
#         domain=[],  # Remove company filtering
#         check_company=False  # Allow locations from all companies
#     )

#     location_dest_id = fields.Many2one(
#         'stock.location',
#         string="Destination Location",
#         domain=[],  # Remove company filtering
#         check_company=False  # Allow locations from all companies
#     )
#     _sql_constraints = []  # Remove all SQL constraints

#     def _check_company_constrains(self):
#         """ Override to remove company constraint validation """
#         if self.env.context.get('force_company_validation', False):
#             return True  # Disable all company validation
#         return super(StockPicking, self)._check_company_constrains()

#     def button_validate(self):
#         """ Override to completely bypass company validation on stock picking """
#         self = self.with_context(skip_company_check=True, force_company_validation=True)  # Force context bypass
#         return super(StockPicking, self).button_validate()

#     def action_confirm(self):
#         """ Override to skip company validation when confirming transfers """
#         for move in self.move_ids:
#             move.company_id = self.company_id  # Sync company ID
#         return super(StockPicking, self).action_confirm()


from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    location_id = fields.Many2one(
        'stock.location',
        string="Source Location",
        required=True,        # 🔥 MUST BE TRUE
        check_company=False
    )

    location_dest_id = fields.Many2one(
        'stock.location',
        string="Destination Location",
        required=True,        # 🔥 MUST BE TRUE
        check_company=False
    )

    def _check_company(self):
        if self.env.context.get('skip_company_check'):
            return
        return super()._check_company()

    @api.model
    def create(self, vals):
        # Absolute safety net
        if vals.get('picking_type_id'):
            picking_type = self.env['stock.picking.type'].browse(vals['picking_type_id'])

            vals.setdefault(
                'location_id',
                picking_type.default_location_src_id.id
            )
            vals.setdefault(
                'location_dest_id',
                picking_type.default_location_dest_id.id
            )

        if not vals.get('location_id'):
            raise ValueError("location_id is missing while creating stock.picking")

        return super().create(vals)

   