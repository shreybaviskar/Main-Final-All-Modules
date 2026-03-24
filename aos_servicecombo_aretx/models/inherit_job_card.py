from odoo import api, fields, models
from dateutil.relativedelta import relativedelta




class InheritJobCardLine(models.Model):
    _inherit = "job.card.line"

    expiry_date=fields.Date(string='Expiry Date', default=fields.Date.context_today)
    check = fields.Boolean(string='check', default=False)
    vehicle_id = fields.Char(string="Vehicle",stored=True)

    @api.onchange('x_product_id')
    def onchange_x_product_id (self):
        for rec in self:
            print("hello i am good")
            if rec.x_product_id:
                print("---",rec.x_product_id,"----")
                print("vahivale", rec.job_id.vehicle.x_vehicle_number_id)
                demo = rec.job_id.vehicle.x_vehicle_number_id
                rec.vehicle_id = demo
                print("vehicle,", rec.vehicle_id)
                if rec.x_product_id.is_service_combo == True:
                        print("---1----",rec.check)
                        rec.check = True
                        my_date_months = rec.expiry_date + relativedelta(months=rec.x_product_id.contract_duration)
                        print("duration of product",rec.x_product_id.contract_duration)
                        print("current date",my_date_months)
                        rec.expiry_date=my_date_months

    @api.model
    def unlink(self):
        # self.service_combo_unlink(res)
        task1_search = self.env['service.combo.tracker'].search([('jobcard_line_id', '=', self.id), (
        'service_combo_id', '=', self.x_product_id.id)])  # call create method of tasks.manager model
        if task1_search:
            # update
            for task1_delete in task1_search:
                task1_delete.unlink()
        res = super(InheritJobCardLine, self).unlink()
        return res

    @api.model
    def write(self, vals):
        res = super(InheritJobCardLine, self).write(vals)
        self.service_combo_write(res)
        return res

    @api.model
    def create(self, vals):
        res = super(InheritJobCardLine, self).create(vals)
        self.service_combo(res)
        return res

    def service_combo(self, res):
        print("hello i am service_bombo action...................")
        job_card_id = res#self.env['job.card.line'].search([])[-1]
        services = self.env['service.combo.item'].search([])
        print("job card id",job_card_id)
        print("job_combo_id",job_card_id.x_product_id.id)
        job_combo_id=job_card_id.x_product_id.id
        print("services",services)
        print("services_combo_id",services.service_combo_id)
        for combo in services:
            if combo.service_combo_id.id == job_combo_id:
                print("yes this is success.......")
                print("combo_id",combo.service_combo_id.id)
                print("service_id",combo.service_id.id)
                print("qunatity",combo.no_of_items)
                if combo.no_of_items == False or combo.no_of_items == 0:
                    #infinite service
                    task1 = self.env['service.combo.tracker']  # call create method of tasks.manager model
                    task1.create({'is_infinite': True, 'expiry_date': job_card_id.expiry_date, 'jobcard_line_id': job_card_id.id,
                                  'service_combo_id': combo.service_combo_id.id,
                                  'service_id': combo.service_id.id, 'state': 'draft'})
                else:
                    for i in range(combo.no_of_items):
                        task1 = self.env['service.combo.tracker']  # call create method of tasks.manager model
                        task1.create({'expiry_date': job_card_id.expiry_date,'jobcard_line_id': job_card_id.id, 'service_combo_id':combo.service_combo_id.id,
                                      'service_id':combo.service_id.id, 'state': 'draft'})


    def service_combo_write(self, res):
        print("hello i am service_bombo action...................")
        job_card_id = self#self.env['job.card.line'].search([])[-1]
        services = self.env['service.combo.item'].search([])
        print("job card id",job_card_id)
        print("job_combo_id",job_card_id.x_product_id.id)
        job_combo_id=job_card_id.x_product_id.id
        print("services",services)
        print("services_combo_id",services.service_combo_id)
        for combo in services:
            if combo.service_combo_id.id == job_combo_id:
                print("yes this is success.......")
                print("combo_id",combo.service_combo_id.id)
                print("service_id",combo.service_id.id)
                print("qunatity",combo.no_of_items)
                if combo.no_of_items == False or combo.no_of_items == 0:
                    #infinite service
                    task1_search = self.env['service.combo.tracker'].search([('jobcard_line_id', '=', job_card_id.id), ('service_combo_id', '=', combo.service_combo_id.id),('service_id', '=', combo.service_id.id)])  # call create method of tasks.manager model
                    if task1_search:
                        # update
                        for task1_update in task1_search:
                            task1_update.write({'is_infinite': True, 'expiry_date': job_card_id.expiry_date,'jobcard_line_id': job_card_id.id,'service_combo_id': combo.service_combo_id.id,'service_id': combo.service_id.id, 'state': 'draft'})
                    else:
                        task1 = self.env['service.combo.tracker']  # call create method of tasks.manager model
                        task1.create({'is_infinite': True, 'expiry_date': job_card_id.expiry_date, 'jobcard_line_id': job_card_id.id,'service_combo_id': combo.service_combo_id.id, 'service_id': combo.service_id.id,'state': 'draft'})

                    # task1 = self.env['service.combo.tracker']  # call create method of tasks.manager model
                    # task1.create({'is_infinite': True, 'expiry_date': job_card_id.expiry_date, 'jobcard_line_id': job_card_id.id,
                    #               'service_combo_id': combo.service_combo_id.id,
                    #               'service_id': combo.service_id.id, 'state': 'draft'})
                else:
                    task1_search = self.env['service.combo.tracker'].search([('jobcard_line_id', '=', job_card_id.id), ('service_combo_id', '=', combo.service_combo_id.id),('service_id', '=', combo.service_id.id)])
                    if task1_search:
                        # update
                        for task1_update in task1_search:
                            task1_update.write({'expiry_date': job_card_id.expiry_date, 'jobcard_line_id': job_card_id.id,'service_combo_id': combo.service_combo_id.id,'service_id': combo.service_id.id, 'state': 'draft'})
                    else:
                        for i in range(combo.no_of_items):
                            task1 = self.env['service.combo.tracker']  # call create method of tasks.manager model
                            task1.create({'expiry_date': job_card_id.expiry_date, 'jobcard_line_id': job_card_id.id,'service_combo_id': combo.service_combo_id.id,'service_id': combo.service_id.id, 'state': 'draft'})
                    # for i in range(combo.no_of_items):
                    #     task1 = self.env['service.combo.tracker']  # call create method of tasks.manager model
                    #     task1.create({'expiry_date': job_card_id.expiry_date,'jobcard_line_id': job_card_id.id, 'service_combo_id':combo.service_combo_id.id,'service_id':combo.service_id.id, 'state': 'draft'})










