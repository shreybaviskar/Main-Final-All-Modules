from odoo import api, fields, models


class AosRoiFile(models.Model):
    _name = "aos.roi.file"
    _description = "Generated ROI Files"

    name = fields.Char(string="Filename", required=True)
    file = fields.Binary(string="File", attachment=True, readonly=True)
    create_date = fields.Datetime(string="Created on", readonly=True)

