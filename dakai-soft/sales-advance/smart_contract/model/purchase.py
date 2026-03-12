import base64
from odoo import fields, models, _
from .utils import *

class Purchase(models.Model):
    _inherit = "purchase.order"

    contract_id = fields.Many2one("smart.contract", _("Contract"))
    
    def action_create_contract(self):
        action_create_contract_util(self, 'purchase')
        
    def action_open_smart_contract(self):
        return action_open_smart_contract_util(self)
    
    def action_add_attachment(self):
        action_add_attachment_util(self)
        
    def action_send_contract_via_message_compose(self):
        return action_send_contract_via_message_compose_util(self)