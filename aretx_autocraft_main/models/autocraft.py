from odoo import api, fields, models
from datetime import datetime, time


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    entry_date = fields.Datetime(string='Entry Date', default=False)
    exit_date = fields.Datetime(string='Exit Date', default=False)


class ProjectTask(models.Model):
    _inherit = 'project.task'

    date_deadline_plain = fields.Datetime(
        string="Deadline",
        related="date_deadline",
        store=True,
        readonly=True
    )

    def action_today_deadline_tasks(self):
        today = fields.Date.context_today(self)
        start = datetime.combine(today, time.min)
        end = datetime.combine(today, time.max)
        print('today')
        print('start')
        print('end')
        print(today)
        print(start)
        print(end)

        return {
            'name': "Today's Deadline Tasks",
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'list,kanban,form',
            'domain': [
                ('date_deadline', '>=', start),
                ('date_deadline', '<=', end),
            ],
            'order': 'date_deadline asc',
        }

    def action_overdue_tasks(self):
        today = fields.Date.context_today(self)
        return {
            'name': "Overdue Task",
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'list,kanban,form',
            'domain': [
                ('date_deadline', '<', today),
                (('state', 'not in', ['1_done', '1_canceled'])),
            ],
            'order': 'date_deadline asc',
        }
