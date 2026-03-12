from odoo import models, fields, api
from odoo.exceptions import UserError


class DynamicProductCut(models.Model):
    _name = 'dynamic.product.cut'
    _description = 'Dynamic Product Cutting'

    name = fields.Char(default="Cut Process")

    product_id = fields.Many2one(
        'product.product',
        string="Parent Product",
        domain=[('product_tmpl_id.is_parent', '=', True)],
        required=True
    )

    line_ids = fields.One2many(
        'dynamic.product.cut.line',
        'cut_id',
        string="Cut Lines"
    )

    def action_process_cut(self):

        ProductTemplate = self.env['product.template']
        location = self.env.ref('stock.stock_location_stock')

        for rec in self:

            parent_product = rec.product_id
            parent_template = parent_product.product_tmpl_id

            parent_length = parent_template.length

            if parent_product.qty_available <= 0:
                raise UserError("No stock available for parent product")

            total_cut_length = 0

            # Calculate total cut
            for line in rec.line_ids:
                total_cut_length += line.length * line.quantity

            if total_cut_length > parent_length:
                raise UserError("Cut length exceeds parent product length")

            remaining_length = parent_length - total_cut_length

            # ---------- Create child products ----------
            for line in rec.line_ids:

                child_name = f"{parent_product.name} {line.length}m"

                product = ProductTemplate.search([
                    ('name', '=', child_name),
                    ('length', '=', line.length),
                    ('is_parent', '=', False)
                ], limit=1)

                if not product:

                    product = ProductTemplate.create({
                        'name': child_name,
                        'length': line.length,
                        'is_parent': False,
                        'uom_id': parent_template.uom_id.id,
                        'is_storable': True,
                    })

                # add stock
                self.env['stock.quant']._update_available_quantity(
                    product.product_variant_id,
                    location,
                    line.quantity
                )

            # ---------- Create remaining piece ----------
            if remaining_length > 0:

                remain_name = f"{parent_product.name} {remaining_length}m"

                remain_product = ProductTemplate.search([
                    ('name', '=', remain_name),
                    ('length', '=', remaining_length),
                    ('is_parent', '=', False)
                ], limit=1)

                if not remain_product:

                    remain_product = ProductTemplate.create({
                        'name': remain_name,
                        'length': remaining_length,
                        'is_parent': False,
                        'uom_id': parent_template.uom_id.id,
                        'is_storable': True,
                    })

                self.env['stock.quant']._update_available_quantity(
                    remain_product.product_variant_id,
                    location,
                    1
                )

            # ---------- Deduct parent stock ----------
            self.env['stock.quant']._update_available_quantity(
                parent_product,
                location,
                -1
            )