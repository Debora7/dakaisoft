from odoo import api, fields, models, _

class Partner(models.Model):
    _inherit = 'res.partner'
    
    smart_contract_ids = fields.One2many("smart.contract", "partner_id", _("Contracts"))
    smart_contract_count = fields.Integer(_("Contracts Number"), compute="_count_smart_contract")

    def _count_smart_contract(self):
        for s in self:
            s.smart_contract_count = len(s.smart_contract_ids.ids)

    def action_open_smart_contract(self):
        self.ensure_one()
        action = self.env.ref('smart_contract.action_smart_contract').read()[0]
        action['domain'] = [('id', 'in', self.smart_contract_ids.ids)]
        return action

class ResBank(models.Model):
    _inherit = "res.partner.bank"

    def first_bank(self):
        return self and self[0].bank_id.name or "..................."

    def first_account(self):
        return self and self[0].acc_number or "..................."

