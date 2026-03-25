from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from datetime import date


class ResPartner(models.Model):
    _inherit = "res.partner"

    mobile = fields.Char(string='Mobile')

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            partners = self.search([
                                       '|', '|', '|', '|', '|',
                                       ('name', operator, name),
                                       ('email', operator, name),
                                       ('ref', operator, name),
                                       ('vat', operator, name),
                                       ('phone', operator, name),
                                       ('mobile', operator, name)
                                   ] + args, limit=limit)
        else:
            partners = self.search(args, limit=limit)
        return [(partner.id, partner.display_name) for partner in partners]


class InheritInvoiceLine(models.Model):
    _inherit = "account.move.line"

    expiry_date = fields.Date(string='Expiry Date')

    @api.onchange('product_id')
    def onchange_product_id(self):
        """Calculate expiry date based on contract duration"""
        for rec in self:
            if rec.product_id and rec.product_id.is_service_combo:
                contract_months = rec.product_id.contract_duration or 0
                if contract_months > 0:
                    expiry_date = fields.Date.context_today(self) + relativedelta(months=contract_months)
                    rec.expiry_date = expiry_date

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set expiry date and create tracker records"""
        lines = super(InheritInvoiceLine, self).create(vals_list)

        for line in lines:
            # Set expiry date for service combo products
            if line.product_id and line.product_id.is_service_combo:
                if not line.expiry_date:
                    contract_months = line.product_id.contract_duration or 0
                    if contract_months > 0:
                        expiry_date = date.today() + relativedelta(months=contract_months)
                        line.expiry_date = expiry_date

            # Create tracker records if invoice is confirmed
            if line.move_id.move_type == 'out_invoice' and line.product_id and line.product_id.is_service_combo:
                self.service_combo([line])

        return lines

    def unlink(self):
        """Delete associated tracker records"""
        for rec in self:
            if rec.move_id.move_type == 'out_invoice':
                trackers = self.env['service.combo.tracker'].search([
                    ('account_move_line_id', '=', rec.id),
                    ('service_combo_id', '=', rec.product_id.id)
                ])
                if trackers:
                    trackers.unlink()
        return super(InheritInvoiceLine, self).unlink()

    def service_combo(self, res):
        """Create tracker records for service combo invoice lines"""
        for move_id in res:
            services = self.env['service.combo.item'].search([])
            order_combo_id = move_id.product_id.id

            for combo in services:
                if combo.service_combo_id.id == order_combo_id:
                    if combo.no_of_items == False or combo.no_of_items == 0:
                        # Infinite service
                        self.env['service.combo.tracker'].create({
                            'is_infinite': True,
                            'expiry_date': move_id.expiry_date,
                            'account_move_line_id': move_id.id,
                            'service_combo_id': combo.service_combo_id.id,
                            'service_id': combo.service_id.id,
                            'state': 'draft'
                        })
                    else:
                        # Create multiple records
                        for i in range(combo.no_of_items):
                            self.env['service.combo.tracker'].create({
                                'expiry_date': move_id.expiry_date,
                                'account_move_line_id': move_id.id,
                                'service_combo_id': combo.service_combo_id.id,
                                'service_id': combo.service_id.id,
                                'state': 'draft'
                            })