from odoo import api, models, fields, _

class Contract(models.Model):
    _inherit = 'smart.contract'
    
    document_type = fields.Selection(selection_add=[("notificare", "Notificare")], ondelete={'notificare': 'set default'})
    
    def _compute_show_regulation(self):
        res = super(Contract, self)._compute_show_regulation()
        if not self.nr_document and self.document_type == 'notificare':
            res = True
        return res
    
    def _get_regulation_required_compute(self):
        res = super(Contract, self)._get_regulation_required_compute()
        if self.document_type=='notificare':
            res = True
        return res
        

class RegulatorNumere(models.Model):
    _inherit = "smart.contract.regulation"
    
    document_type = fields.Selection(selection_add=[("notificare", "Notificare")], ondelete={'notificare': 'set default'})

class smartContractTemplate(models.Model):
    _inherit = "smart.contract.template"
    
    document_type = fields.Selection(selection_add=[("notificare", "Notificare")], ondelete={'notificare': 'set default'})
    