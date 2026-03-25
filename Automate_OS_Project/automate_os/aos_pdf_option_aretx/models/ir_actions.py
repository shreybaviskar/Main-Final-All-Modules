# -*- coding: utf-8 -*-
from odoo import models, fields


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    default_print_option = fields.Selection(
        [
            ("print", "Print"),
            ("download", "Download"),
            ("open", "Open"),
        ],
        string="Default Printing Option",
    )

    def _get_readable_fields(self):
        fields_set = super()._get_readable_fields()
        fields_set.add("default_print_option")
        return fields_set

    def report_action(self, docids, data=None, config=True):
        action = super().report_action(docids, data=data, config=config)

        # REQUIRED FOR ODOO 19
        action.setdefault("context", dict(self.env.context))

        action["id"] = self.id
        action["default_print_option"] = self.default_print_option

        return action
