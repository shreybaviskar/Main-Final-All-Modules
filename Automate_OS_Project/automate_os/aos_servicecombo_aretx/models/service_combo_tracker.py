from odoo import api, fields, models
from datetime import datetime


class ComboCreate(models.Model):
    _name = "service.combo.tracker"
    _description = "Service Combo Tracker"

    # Only Sale Order and Invoice related fields (NO job card)
    account_move_line_id = fields.Many2one('account.move.line', string='Invoice ID', readonly=True, ondelete="cascade")
    saleorder_line_id = fields.Many2one('sale.order.line', string='Sale Order ID', readonly=True, ondelete="cascade")

    # Link back to combo master (for One2many relationship)
    combo_master_id = fields.Many2one('service.combo.master', string='Combo Master', ondelete='cascade')

    # Vehicle fields - Multi-level related fields (order_id > x_vehicle_number_id)
    vehicle_sale_order = fields.Many2one(
        'vehicle.master.model',
        string='Sale Order Vehicle',
        related='saleorder_line_id.order_id.x_vehicle_number_id',
        readonly=True,
        store=True
    )
    vehicle_invoice = fields.Many2one(
        'vehicle.master.model',
        string='Invoice Vehicle',
        related='account_move_line_id.move_id.vehicle_number',
        readonly=True,
        store=True
    )

    # Display names for tree view
    vehicle_sale_order_display = fields.Char(
        string='Sale Order Vehicle Number',
        related='vehicle_sale_order.x_vehicle_number_id',
        readonly=True,
        store=True
    )
    vehicle_invoice_display = fields.Char(
        string='Invoice Vehicle Number',
        related='vehicle_invoice.x_vehicle_number_id',
        readonly=True,
        store=True
    )

    # Customer fields
    sale_order_id = fields.Many2one(
        'res.partner',
        string='Sale Order Customer',
        related="saleorder_line_id.order_id.partner_id",
        readonly=True,
        store=True
    )
    account_move_id = fields.Many2one(
        'res.partner',
        string='Invoice Customer',
        related="account_move_line_id.move_id.partner_id",
        readonly=True,
        store=True
    )

    expiry_date = fields.Date(string='Expiry Date', default=fields.Date.context_today, readonly=True)
    service_combo_id = fields.Many2one('product.template', string='Service Combo', readonly=True)
    service_id = fields.Many2one('product.template', string='Service', readonly=True)

    state = fields.Selection([
        ('draft', 'Pending'),
        ('cancle', 'Cancelled'),
        ('done', 'Done'),
    ], default='draft', string="Status")

    completed_date = fields.Date(string='Completed Date')
    description = fields.Char(string='Description')
    is_infinite = fields.Boolean(string='Is Infinite', default=False, readonly=True)

    def add_combo(self):
        """Add new combo entry based on context"""
        task1 = self.env['service.combo.tracker']

        if self._context.get('saleorder_line_id'):
            task1.create({
                'is_infinite': False,
                'expiry_date': self._context.get('expiry_date'),
                'saleorder_line_id': self._context.get('saleorder_line_id'),
                'completed_date': fields.Date.today(),
                'service_combo_id': self._context.get('service_combo_id'),
                'service_id': self._context.get('service_id'),
                'state': 'done'
            })

        if self._context.get('account_move_line_id'):
            task1.create({
                'is_infinite': False,
                'expiry_date': self._context.get('expiry_date'),
                'account_move_line_id': self._context.get('account_move_line_id'),
                'completed_date': fields.Date.today(),
                'service_combo_id': self._context.get('service_combo_id'),
                'service_id': self._context.get('service_id'),
                'state': 'done'
            })

    def view_partner(self):
        """View partner/customer details"""
        res_id = False
        if self.sale_order_id.id:
            res_id = self.sale_order_id.id
        elif self.account_move_id.id:
            res_id = self.account_move_id.id

        return {
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': res_id,
            'context': {'create': False},
            'nodestroy': True,
            'target': 'new'
        }

    def edit_combo(self):
        """Edit combo entry"""
        return {
            'res_model': 'service.combo.tracker',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.id,
            'context': {'create': False},
            'nodestroy': True,
            'target': 'new'
        }