import os
from odoo import models, fields, api
from odoo.tools import config
import math


class DatabaseMonitor(models.Model):
    _name = 'database.monitor'
    _description = 'Database Storage Monitor'

    name = fields.Char(
        string='Database Name',
        compute='_compute_db_name',
        store=True
    )

    db_storage_mb = fields.Float(
        string='Database Size (MB)',
        compute='_compute_storage',
        store=False
    )

    file_storage_mb = fields.Float(
        string='Filestore Size (MB)',
        compute='_compute_storage',
        store=False
    )

    attachment_table_mb = fields.Float(
        string='Attachments Size (MB)',
        compute='_compute_storage',
        store=False
    )

    space_allocation = fields.Float(
        string='Allocated Storage (MB)',
        compute='_compute_storage',
        store=False
    )

    used_storage_mb = fields.Float(
        string='Used Storage (MB)',
        compute='_compute_storage',
        store=False
    )

    storage_usage_text = fields.Char(
        string='Storage Usage',
        compute='_compute_storage',
        store=False
    )

    storage_usage_percent = fields.Float(
        string='Storage Usage (%)',
        compute='_compute_storage',
        store=False
    )

    storage_percent = fields.Float(
        string='Storage %',
        compute='_compute_storage'
    )

    show_storage_warning = fields.Boolean(
        string='Show Storage Warning',
        compute='_compute_storage',
        store=False
    )

    def _compute_db_name(self):
        for rec in self:
            rec.name = self.env.cr.dbname

    def _compute_storage(self):
        # Attachments logical size
        self.env.cr.execute("""
                            SELECT COALESCE(SUM(file_size), 0)
                            FROM ir_attachment
                            """)
        logical_bytes = self.env.cr.fetchone()[0]
        logical_mb = round(logical_bytes / (1024 * 1024), 2)

        # Database physical size
        self.env.cr.execute("SELECT pg_database_size(current_database());")
        db_mb = round(self.env.cr.fetchone()[0] / (1024 * 1024), 2)

        # Allocated space from settings
        allocated_mb = float(
            self.env['ir.config_parameter']
            .sudo()
            .get_param('storage.space.allocation.mb', 0)
        )

        # ✅ USED = DB + FILESTORE
        used_mb = round(db_mb + logical_mb, 2)

        for rec in self:
            rec.db_storage_mb = db_mb
            rec.file_storage_mb = logical_mb
            rec.attachment_table_mb = logical_mb
            rec.space_allocation = allocated_mb
            rec.used_storage_mb = used_mb

            # ✅ STORAGE PERCENT (for progress bar)
            if allocated_mb > 0:
                percent = (used_mb / allocated_mb) * 100
            else:
                percent = 0.0

            rec.storage_percent = min(round(percent, 2), 100.0)

            # ✅ Set warning flag if storage > 90%
            rec.show_storage_warning = rec.storage_percent >= 90.0

            # Display text like Google Drive
            def to_gb(mb):
                return round(mb / 1024, 2)

            if allocated_mb >= 1024:
                rec.storage_usage_text = (
                    f"{to_gb(used_mb)} GB of {to_gb(allocated_mb)} GB used"
                )
            else:
                rec.storage_usage_text = (
                    f"{used_mb} MB of {allocated_mb} MB used"
                )

    @api.model
    def action_open_database_monitor(self):
        db_name = self.env.cr.dbname

        record = self.search([('name', '=', db_name)], limit=1)
        if not record:
            record = self.create({'name': db_name})

        return {
            'type': 'ir.actions.act_window',
            'name': 'Database Monitor',
            'res_model': 'database.monitor',
            'view_mode': 'form',
            'res_id': record.id,
            'target': 'current',
        }

    def action_get_more_storage(self):
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.odoo.com/pricing',
            'target': 'new'
        }

    @api.model
    def is_storage_limit_exceeded(self):
        """Check if storage has reached 100% or more"""
        allocated_mb = float(
            self.env['ir.config_parameter']
            .sudo()
            .get_param('storage.space.allocation.mb', 0)
        )

        if allocated_mb == 0:
            return False

        # Database size
        self.env.cr.execute("SELECT pg_database_size(current_database());")
        db_mb = self.env.cr.fetchone()[0] / (1024 * 1024)

        # Attachments size
        self.env.cr.execute("""
                            SELECT COALESCE(SUM(file_size), 0)
                            FROM ir_attachment
                            """)
        att_mb = self.env.cr.fetchone()[0] / (1024 * 1024)

        # Total used
        used_mb = db_mb + att_mb

        # Calculate percentage
        usage_percent = (used_mb / allocated_mb) * 100

        return usage_percent >= 100.0


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    space_allocation_mb = fields.Float(
        string='Allocated Storage Space (MB)',
        help='Odoo साठी allocate केलेली logical storage limit (MB मध्ये)',
        config_parameter='storage.space.allocation.mb'
    )