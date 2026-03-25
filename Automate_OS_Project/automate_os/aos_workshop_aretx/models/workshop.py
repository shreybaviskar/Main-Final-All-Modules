from odoo import models, fields, api
from datetime import datetime


class AretxWorkshop(models.Model):
    _inherit = 'vehicle.master.model'

    variant = fields.Char(string='Variant')
    chassis_number = fields.Char(string='Chassis Number')
    engine_number = fields.Char(string='Engine Number')
    fuel_type = fields.Char(string='Fuel Type')

    def _get_years(self):
        current_year = datetime.now().year
        return [(str(y), str(y)) for y in range(current_year, 1799, -1)]

    year = fields.Selection(
        selection=_get_years,
        string="Year"
    )


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    technician_id_l = fields.Many2one(
        'res.partner', string='Technician',
        domain="[('category_id.name', '=', 'Technician')]")


class WorkshopAccountMove(models.Model):
    _inherit = "account.move"

    service_type = fields.Char(string='Service Type')
    advisor_name = fields.Many2one(
        'res.partner', string='Advisor Name' ,
        domain="[('category_id.name', '=', 'Advisor')]")
    
    @api.model
    def create(self, vals):
        move = super().create(vals)

        if move.move_type in ('out_invoice', 'out_refund') and move.invoice_origin:
            sale = self.env['sale.order'].search(
                [('name', '=', move.invoice_origin)],
                limit=1
            )
            if sale:
                move.service_type = sale.service_type
                move.advisor_name = sale.advisor_name

        return move

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    service_type = fields.Char(string='Service Type')

    advisor_name = fields.Many2one(
        'res.partner', string='Advisor Name' ,
        domain="[('category_id.name', '=', 'Advisor')]")

    technician_id = fields.Many2one(
        'res.users', string='Technician')
    entry_date = fields.Datetime(
        string='Entry Date', default=False)
    exit_date = fields.Datetime(
        string='Exit Date', default=False)


class VehicleMaster(models.Model):
    _inherit = "vehicle.master.model"


    def view_in_sale(self):
        return {
            'name': self.x_vehicle_number_id,
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'domain': [('x_vehicle_number_id', '=', self.x_vehicle_number_id)],
            'target': 'list'
        }