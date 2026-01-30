from odoo.exceptions import UserError
from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet


class Warranty(models.Model):
    _inherit = 'account.move'

    warranty_number = fields.Char(string="Warranty Number")