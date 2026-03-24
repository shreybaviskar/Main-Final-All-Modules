from odoo import api, fields, models

class ServiceStatusMaster(models.Model):
    _name = "service.status.master"
    _description = "service status Master"

    # id = fields.Integer(string="Id", store=True)
    # display_name = fields.Char(string="Name", store=True)
    # vehicle = fields.Char(string="Vehicle", store=True)
    # brand = fields.Char(string="Brand", store=True)
    # model = fields.Char(string="Model", store=True)

    name = fields.Char(string="Name")
    customer = fields.Many2one('res.partner', string='Customer', tracking=True, store=False)
    customer_name = fields.Char(string='Customer Name', index=True, required=False, inverse='_compute_customer_name',compute='_compute_partner', readonly=False)
    customer_phone = fields.Char(string='Customer Phone', index=True, required=False, inverse='_compute_customer_phone',compute='_compute_partner_phone', readonly=False)
    vehicle = fields.Many2one('vehicle.master.model', string='Vehicle', tracking=True, store=False)
    vehicle_number = fields.Char(string='Vehicle Number', index=True, required=False, inverse='_compute_vehicle_number',compute='_compute_vehicle', readonly=False)
    expiry_date = fields.Date(string='Expiry Date')
    date_range = fields.Date(string='Select Date Range',index=True,tracking=True)
    # date_range1 = fields.Datetime(string='Select Date Range')
    # start_date = fields.Date(string='Select Date', help="Default start date to search.")
    start_date = fields.Date(string='Select Start Date', help="Default start date to search.")
    end_date = fields.Date(string='End Date', help="Default end date to search.")
    # status_line_id = fields.One2many('service.status.master', string="Sale Order line", store=False)
    saleorder_line_id = fields.One2many('service.combo.tracker', string="Sale Order line", store=False)
    saleorder_lines = fields.One2many('sale.order.line', domain="[('id', '=', '0')]", string="Sale Order line", store=False)
    account_move_lines = fields.One2many('account.move.line', domain="[('id', '=', '0')]", string="Invoice line", store=False)
    service_id = fields.Many2one('product.template', domain="[('type', '=', 'service')]", string='Select Service',readonly=False, store=False)
    # mydata = fields.One2many('service.status.master', string="Sale Order line", store=False)


    # customer_name = fields.Char(string="Name", store=True)
    # content = fields.Text(string='Content', index=True, required=True, tracking=True, related='template_id.description', store=True, readonly=False)

    # vehicle_number = fields.Text(string='Vehicle Number', index=True, required=False, tracking=True, inverse='_compute_vehicle_number',compute='_compute_x_vehicle_number_id', store=True, readonly=False)

    # service_id = fields.Many2one('service.combo.tracker', domain="[('saleorder_line_id', '!=', None)]", string='Services', tracking=True, store=True)
    # vehicle = fields.Many2one('vehicle.master.model', string='Vehicle', tracking=True,store=True)
    # brand = fields.Many2one('vehicle.brand.model', string="Brand Name", related='vehicle.x_brand_id', store=True)
    # model = fields.Many2one('vehicle.model.model', string="Model", related='vehicle.x_model_id', store=True)

    @api.depends('customer.name')
    def _compute_partner(self):
        for rec in self:
            rec.customer_name = rec.customer.name

    def _compute_customer_name(self):
        pass

    @api.depends('customer.phone')
    def _compute_partner(self):
        for rec in self:
            rec.customer_phone = rec.customer.phone

    def _compute_partner_phone(self):
        pass

    @api.depends('vehicle.x_vehicle_number_id')
    def _compute_vehicle(self):
        for rec in self:
            rec.vehicle_number = rec.vehicle.x_vehicle_number_id

    def _compute_vehicle_number(self):
        pass
    #
    @api.onchange('service_id','start_date','end_date')
    def _on_change_date_ranges(self):
        # print('asdasdasdas')
        for rec in self:
            print('rec.date_range')
            print(rec.service_id)
            print(rec.start_date)
            print(rec.end_date)

            if rec.service_id and rec.start_date and rec.end_date:
                #filter
                #get data from sale order line by this service and this between dates

                rec.saleorder_lines = self.env['sale.order.line'].search([('product_template_id', '=', rec.service_id.id), ('order_id.date_order', '>=', rec.start_date), ('order_id.date_order', '<=', rec.end_date), ('order_id.state', 'in', ['sale', 'done'])])

                rec.account_move_lines = self.env['account.move.line'].search([('product_id.product_tmpl_id', '=', rec.service_id.id), ('move_id.move_type', '=', 'out_invoice'), ('move_id.invoice_date', '>=', rec.start_date), ('move_id.invoice_date', '<=', rec.end_date), ('move_id.state', 'in', ['posted', 'done'])])


                # saleorder_line_id = self.env['sale.order.line'].read_group()
                print(rec.saleorder_lines)
            else:
                rec.saleorder_lines = None

            print('rec.date_range')

    # @api.onchange('vehicle')
    # def _change_vehicle(self):
    #     self.jobcard_line_id = None
    #     for rec in self:
    #         if rec.vehicle.x_customer_id is not False:
    #             print(rec.vehicle.x_customer_id)
    #             customer_ids = []
    #             for c_id in rec.vehicle.x_customer_id:
    #                 customer_ids.append(c_id.id)
    #             print(customer_ids)
    #             if len(customer_ids) > 0:
    #                 # self.customer = rec.vehicle.x_customer_id
    #                 # print([rec.vehicle.x_customer_id.id])
    #                 job_card = self.env['job.card'].search([('vehicle', '=', rec.vehicle.id),('partner_id', 'in', customer_ids)])
    #                 # print(dir(job_card.x_job_card_ids))
    #                 ids = []
    #                 for line in job_card.x_job_card_ids:
    #                     # ids.append(str(line.id)+str(datetime.today()))
    #                     ids.append(line.id)
    #                 if len(ids) > 0:
    #                     self.jobcard_line_id = self.env['service.combo.tracker'].search([('jobcard_line_id', 'in', ids)])
    #                     # self.jobcard_line_id = self.env['service.combo.tracker'].search([('jobcard_line_id', 'in', ids)])
    #
    #                 else:
    #                     self.jobcard_line_id = None
    #
    #     # print('asdasdasd')
    #     # print('asdasdasd')
    #     # print('asdasdasd')
    #     # print(self.x_job_card_line_ids)
    #     # print(dir(self.x_job_card_line_ids))
    #     # print(self.x_job_card_line_ids.service_combo_id.name)
    #     # print('asdasdasd')
    #
    @api.model
    def default_get(self, fields):
        rec = super(ServiceStatusMaster, self).default_get(fields)

        # for rec in self:
        #     if rec.vehicle.x_customer_id is not False:
        #         print(rec.vehicle.x_customer_id)
        #         customer_ids = []
        #         for c_id in rec.vehicle.x_customer_id:
        #             customer_ids.append(c_id.id)
        #         print(customer_ids)
        #         if len(customer_ids) > 0:
        #             # self.customer = rec.vehicle.x_customer_id
        #             # print([rec.vehicle.x_customer_id.id])
        #             job_card = self.env['job.card'].search([('vehicle', '=', rec.vehicle.id),('partner_id', 'in', customer_ids)])
        #             # print(dir(job_card.x_job_card_ids))
        #             ids = []
        #             for line in job_card.x_job_card_ids:
        #                 # ids.append(str(line.id)+str(datetime.today()))
        #                 ids.append(line.id)
        #             if len(ids) > 0:
        #                 rec.jobcard_line_id = self.env['service.combo.tracker'].search([('jobcard_line_id', 'in', ids)])
        #
        #             else:
        #                 rec.jobcard_line_id = None

        return rec
