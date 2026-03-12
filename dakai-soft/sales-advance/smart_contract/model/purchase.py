import base64
from odoo import fields, models, _


class Purchase(models.Model):
    _inherit = "purchase.order"

    contract_id = fields.Many2one("smart.contract", _("Contract"))