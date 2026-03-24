from odoo import api, fields, models, Command
import logging

_logger = logging.getLogger(__name__)


class ComboCreateMaster(models.Model):
    _name = "service.combo.master"
    _description = "Service Combo Master"

    name = fields.Char(string="Name", compute='_compute_name', store=True)
    vehicle = fields.Many2one('vehicle.master.model', string='Vehicle', store=True)
    brand = fields.Many2one('vehicle.brand.model', string="Brand Name", related='vehicle.x_brand_id', store=True)
    model = fields.Many2one('vehicle.model.model', string="Model", related='vehicle.x_model_id', store=True)

    # Display field to show count
    tracker_count = fields.Integer(
        string="Service Count",
        compute='_compute_tracker_count',
        store=False
    )

    # Service combo tracker lines
    jobcard_line_id = fields.One2many(
        'service.combo.tracker',
        'combo_master_id',
        string="Service Combo Lines"
    )

    @api.depends('vehicle')
    def _compute_name(self):
        """Auto-generate name from vehicle number"""
        for rec in self:
            if rec.vehicle and rec.vehicle.x_vehicle_number_id:
                rec.name = f"Subscription - {rec.vehicle.x_vehicle_number_id}"
            else:
                rec.name = "New Subscription"

    @api.depends('jobcard_line_id')
    def _compute_tracker_count(self):
        """Count tracker records"""
        for rec in self:
            rec.tracker_count = len(rec.jobcard_line_id)

    def _get_tracker_records(self):
        """Get tracker records for this vehicle from sale orders and invoices"""
        if not self.vehicle:
            _logger.info("=== NO VEHICLE SELECTED ===")
            return self.env['service.combo.tracker']

        _logger.info(
            f"=== SEARCHING TRACKERS FOR VEHICLE: {self.vehicle.x_vehicle_number_id} (ID: {self.vehicle.id}) ===")

        tracker_ids = []

        # Method 1: Get from sale orders with this vehicle
        _logger.info("--- Searching Sale Orders ---")
        sale_orders = self.env['sale.order'].search([
            ('x_vehicle_number_id', '=', self.vehicle.id)
        ])
        _logger.info(f"Found {len(sale_orders)} sale orders: {sale_orders.mapped('name')}")

        if sale_orders:
            # Get all order lines with service combo products
            sale_lines = self.env['sale.order.line'].search([
                ('order_id', 'in', sale_orders.ids),
                ('product_template_id.is_service_combo', '=', True)
            ])
            _logger.info(f"Found {len(sale_lines)} service combo lines in sale orders")
            _logger.info(f"Products: {sale_lines.mapped('product_template_id.name')}")

            if sale_lines:
                # Search for trackers linked to these sale order lines
                sale_trackers = self.env['service.combo.tracker'].search([
                    ('saleorder_line_id', 'in', sale_lines.ids)
                ])
                _logger.info(f"Found {len(sale_trackers)} trackers from sale orders")
                tracker_ids.extend(sale_trackers.ids)

        # Method 2: Get from invoices with this vehicle
        _logger.info("--- Searching Invoices ---")
        invoices = self.env['account.move'].search([
            ('vehicle_number', '=', self.vehicle.id),
            ('move_type', 'in', ['out_invoice', 'out_refund'])
        ])
        _logger.info(f"Found {len(invoices)} invoices: {invoices.mapped('name')}")

        if invoices:
            # Get all invoice lines with service combo products
            invoice_lines = self.env['account.move.line'].search([
                ('move_id', 'in', invoices.ids),
                ('product_id.is_service_combo', '=', True)
            ])
            _logger.info(f"Found {len(invoice_lines)} service combo lines in invoices")
            _logger.info(f"Products: {invoice_lines.mapped('product_id.name')}")

            if invoice_lines:
                # Search for trackers linked to these invoice lines
                invoice_trackers = self.env['service.combo.tracker'].search([
                    ('account_move_line_id', 'in', invoice_lines.ids)
                ])
                _logger.info(f"Found {len(invoice_trackers)} trackers from invoices")
                tracker_ids.extend(invoice_trackers.ids)

        # Get unique tracker records
        if tracker_ids:
            trackers = self.env['service.combo.tracker'].browse(list(set(tracker_ids)))
            _logger.info(f"=== TOTAL TRACKERS FOUND: {len(trackers)} ===")
            return trackers
        else:
            _logger.info("=== NO TRACKERS FOUND ===")
            return self.env['service.combo.tracker']

    @api.onchange('vehicle')
    def _onchange_vehicle(self):
        """Update tracker lines when vehicle changes - this runs in the UI"""
        _logger.info(f"=== ONCHANGE VEHICLE TRIGGERED ===")

        # Clear existing lines first using Command.clear()
        self.jobcard_line_id = [Command.clear()]

        if not self.vehicle:
            _logger.info("Vehicle cleared, returning")
            return

        # Get tracker records for this vehicle
        trackers = self._get_tracker_records()

        if not trackers:
            _logger.info("No trackers found to display")
            return

        # Link the trackers to this master record using Command.set()
        _logger.info(f"Setting {len(trackers)} trackers in jobcard_line_id")
        self.jobcard_line_id = [Command.set(trackers.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        """On create, link tracker records to the master"""
        records = super(ComboCreateMaster, self).create(vals_list)

        for record in records:
            if record.vehicle:
                # Get tracker records
                trackers = record._get_tracker_records()

                if trackers:
                    # Link them by setting combo_master_id
                    trackers.write({'combo_master_id': record.id})
                    _logger.info(f"Linked {len(trackers)} trackers to master record {record.id}")

        return records

    def write(self, vals):
        """Update tracker links when vehicle changes"""
        res = super(ComboCreateMaster, self).write(vals)

        if 'vehicle' in vals:
            for rec in self:
                # Clear old links from previous vehicle
                old_trackers = self.env['service.combo.tracker'].search([
                    ('combo_master_id', '=', rec.id)
                ])
                if old_trackers:
                    old_trackers.write({'combo_master_id': False})
                    _logger.info(f"Cleared {len(old_trackers)} old tracker links")

                # Set new links for new vehicle
                if rec.vehicle:
                    trackers = rec._get_tracker_records()
                    if trackers:
                        trackers.write({'combo_master_id': rec.id})
                        _logger.info(f"Linked {len(trackers)} new trackers")

        return res

    def unlink(self):
        """Clear combo_master_id from tracker records before deleting"""
        for rec in self:
            trackers = self.env['service.combo.tracker'].search([
                ('combo_master_id', '=', rec.id)
            ])
            if trackers:
                trackers.write({'combo_master_id': False})

        return super(ComboCreateMaster, self).unlink()

    def action_refresh_trackers(self):
        """Manual action to refresh tracker records"""
        for rec in self:
            if rec.vehicle:
                # Clear old links
                old_trackers = self.env['service.combo.tracker'].search([
                    ('combo_master_id', '=', rec.id)
                ])
                old_trackers.write({'combo_master_id': False})

                # Get and link new trackers
                trackers = rec._get_tracker_records()
                if trackers:
                    trackers.write({'combo_master_id': rec.id})
                    _logger.info(f"Refreshed: Linked {len(trackers)} trackers")

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_debug_info(self):
        """Debug action to check what's happening"""
        self.ensure_one()

        message = f"""
=== DEBUG INFO ===
Vehicle: {self.vehicle.x_vehicle_number_id if self.vehicle else 'None'}
Vehicle ID: {self.vehicle.id if self.vehicle else 'None'}

"""
        if self.vehicle:
            # Sale Orders
            sale_orders = self.env['sale.order'].search([
                ('x_vehicle_number_id', '=', self.vehicle.id)
            ])
            message += f"Sale Orders: Found {len(sale_orders)} orders\n"
            for so in sale_orders:
                message += f"  - {so.name} (State: {so.state})\n"
                for line in so.order_line:
                    is_combo = line.product_template_id.is_service_combo if hasattr(line.product_template_id,
                                                                                    'is_service_combo') else False
                    message += f"    * {line.product_template_id.name} (is_service_combo: {is_combo})\n"

                    # Check trackers for this line
                    line_trackers = self.env['service.combo.tracker'].search([
                        ('saleorder_line_id', '=', line.id)
                    ])
                    message += f"      Trackers for this line: {len(line_trackers)}\n"

            # Invoices
            invoices = self.env['account.move'].search([
                ('vehicle_number', '=', self.vehicle.id)
            ])
            message += f"\nInvoices: Found {len(invoices)} invoices\n"
            for inv in invoices:
                message += f"  - {inv.name} (Type: {inv.move_type})\n"
                for line in inv.invoice_line_ids:
                    if line.product_id:
                        is_combo = line.product_id.is_service_combo if hasattr(line.product_id,
                                                                               'is_service_combo') else False
                        message += f"    * {line.product_id.name} (is_service_combo: {is_combo})\n"

                        # Check trackers for this line
                        line_trackers = self.env['service.combo.tracker'].search([
                            ('account_move_line_id', '=', line.id)
                        ])
                        message += f"      Trackers for this line: {len(line_trackers)}\n"

            # Total trackers via _get_tracker_records()
            all_trackers = self._get_tracker_records()
            message += f"\n=== TOTAL TRACKERS (via _get_tracker_records): {len(all_trackers)} ===\n"

            # Direct search on tracker table
            direct_sale_trackers = self.env['service.combo.tracker'].search([
                ('saleorder_line_id', '!=', False),
                ('saleorder_line_id.order_id.x_vehicle_number_id', '=', self.vehicle.id)
            ])
            message += f"Direct Sale Order Trackers: {len(direct_sale_trackers)}\n"

            direct_invoice_trackers = self.env['service.combo.tracker'].search([
                ('account_move_line_id', '!=', False),
                ('account_move_line_id.move_id.vehicle_number', '=', self.vehicle.id)
            ])
            message += f"Direct Invoice Trackers: {len(direct_invoice_trackers)}\n"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Debug Information',
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }

    @api.model
    def action_open_subscription_form(self):
        """Open subscription form - create new if none exists or open latest"""
        # Check if any record exists
        latest_record = self.search([], order='id desc', limit=1)

        if latest_record:
            # Open the latest record
            res_id = latest_record.id
        else:
            # Create a new record
            new_record = self.create({
                'name': 'New Subscription'
            })
            res_id = new_record.id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Subscription',
            'res_model': 'service.combo.master',
            'view_mode': 'form',
            'res_id': res_id,
            'target': 'current',
        }