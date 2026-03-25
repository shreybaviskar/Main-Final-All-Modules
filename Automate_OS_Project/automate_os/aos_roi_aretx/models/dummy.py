# Dummy module to keep models package importable.
from odoo import models

class Dummy(models.AbstractModel):
    _name = "aos.roi.dummy"
    _description = "Dummy model for package"

