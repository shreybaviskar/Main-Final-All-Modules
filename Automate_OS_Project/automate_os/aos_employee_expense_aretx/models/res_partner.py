# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Related Employee',
        readonly=True
    )

    employee_count = fields.Integer(
        string='Employee Count',
        compute='_compute_employee_count'
    )

    @api.depends('employee_id')
    def _compute_employee_count(self):
        for partner in self:
            partner.employee_count = 1 if partner.employee_id else 0

    # 🔥 MAIN FIX: UNIQUE RECORDS IN TREE VIEW
    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        if self.env.context.get('show_unique_contacts'):
            self.env.cr.execute("""
                SELECT MIN(id)
                FROM res_partner
                WHERE active = true
                GROUP BY LOWER(TRIM(name))
            """)
            unique_ids = [row[0] for row in self.env.cr.fetchall()]
            domain = domain + [('id', 'in', unique_ids)]

        return super()._search(domain, offset, limit, order, **kwargs)

    # ---------------- SMART BUTTONS ---------------- #

    def action_create_employee(self):
        self.ensure_one()

        if self.employee_id:
            raise UserError('This contact already has an employee.')

        if self.is_company:
            raise UserError('Cannot create employee from a company.')

        employee = self.env['hr.employee'].create({
            'name': self.name,
        })

        vals = {}
        if self.phone:
            vals['work_phone'] = self.phone
        if self.mobile:
            vals['mobile_phone'] = self.mobile
        if self.email:
            vals['work_email'] = self.email

        if vals:
            employee.write(vals)

        self.employee_id = employee.id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Employee',
            'res_model': 'hr.employee',
            'res_id': employee.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_employee(self):
        self.ensure_one()

        if not self.employee_id:
            raise UserError('No employee linked.')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Employee',
            'res_model': 'hr.employee',
            'res_id': self.employee_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
