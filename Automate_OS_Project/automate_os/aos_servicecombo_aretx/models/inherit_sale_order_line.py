from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class InheritSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    expiry_date = fields.Date(string='Expiry Date', default=fields.Date.context_today)

    @api.onchange('product_template_id')
    def onchange_product_template_id(self):
        """Calculate expiry date based on contract duration"""
        for rec in self:
            if rec.product_template_id and rec.product_template_id.is_service_combo:
                contract_months = rec.product_template_id.contract_duration or 0
                if contract_months > 0:
                    expiry_date = fields.Date.context_today(self) + relativedelta(months=contract_months)
                    rec.expiry_date = expiry_date

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set expiry date only"""
        lines = super(InheritSaleOrderLine, self).create(vals_list)

        for line in lines:
            # Set expiry date for service combo products
            if line.product_template_id and line.product_template_id.is_service_combo:
                if not line.expiry_date:
                    contract_months = line.product_template_id.contract_duration or 0
                    if contract_months > 0:
                        expiry_date = fields.Date.context_today(self) + relativedelta(months=contract_months)
                        line.expiry_date = expiry_date

        return lines

    def write(self, vals):
        """Update tracker records when expiry date changes"""
        res = super(InheritSaleOrderLine, self).write(vals)

        if 'expiry_date' in vals:
            for line in self:
                trackers = self.env['service.combo.tracker'].search([
                    ('saleorder_line_id', '=', line.id)
                ])
                if trackers:
                    trackers.write({'expiry_date': vals['expiry_date']})

        return res

    def unlink(self):
        """Delete associated tracker records"""
        for rec in self:
            trackers = self.env['service.combo.tracker'].search([
                ('saleorder_line_id', '=', rec.id),
                ('service_combo_id', '=', rec.product_template_id.id)
            ])
            if trackers:
                trackers.unlink()
        return super(InheritSaleOrderLine, self).unlink()

    def service_combo(self, res):
        """Create tracker records for service combo sale order lines"""
        for order_id in res:
            services = self.env['service.combo.item'].search([])
            order_combo_id = order_id.product_template_id.id

            for combo in services:
                if combo.service_combo_id.id == order_combo_id:
                    if combo.no_of_items == False or combo.no_of_items == 0:
                        # Infinite service
                        self.env['service.combo.tracker'].create({
                            'is_infinite': True,
                            'expiry_date': order_id.expiry_date,
                            'saleorder_line_id': order_id.id,
                            'service_combo_id': combo.service_combo_id.id,
                            'service_id': combo.service_id.id,
                            'state': 'draft'
                        })
                    else:
                        # Create multiple records
                        for i in range(combo.no_of_items):
                            self.env['service.combo.tracker'].create({
                                'expiry_date': order_id.expiry_date,
                                'saleorder_line_id': order_id.id,
                                'service_combo_id': combo.service_combo_id.id,
                                'service_id': combo.service_id.id,
                                'state': 'draft'
                            })



class InheritSaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        """Override confirm to create trackers for service combo products"""
        res = super(InheritSaleOrder, self).action_confirm()

        _logger.info("=== SALE ORDER CONFIRMATION - Creating Trackers ===")
        _logger.info(
            f"Order: {self.name}, Vehicle: {self.x_vehicle_number_id.x_vehicle_number_id if self.x_vehicle_number_id else 'None'}")

        # Create trackers for all service combo lines
        for line in self.order_line:
            if line.product_template_id and line.product_template_id.is_service_combo:
                _logger.info(f"Processing service combo: {line.product_template_id.name}")

                # Check if trackers already exist
                existing_trackers = self.env['service.combo.tracker'].search([
                    ('saleorder_line_id', '=', line.id)
                ])

                if existing_trackers:
                    _logger.info(f"Trackers already exist for line {line.id}, skipping...")
                    continue

                # Create trackers
                _logger.info(f"Creating trackers for line {line.id}")
                line.service_combo([line])
            else:
                product_name = line.product_template_id.name if line.product_template_id else 'Unknown'
                is_combo = line.product_template_id.is_service_combo if line.product_template_id else False
                _logger.info(f"Skipping product: {product_name} (is_service_combo: {is_combo})")

        return res