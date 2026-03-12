from odoo import api, models, fields, _
from datetime import datetime, date

class Contract(models.Model):
    _inherit = 'smart.contract'
    
    document_type = fields.Selection(selection_add=[("gdpr", "GDPR")], ondelete={'gdpr': 'set default'})
    
    def _compute_show_regulation(self):
        res = super(Contract, self)._compute_show_regulation()
        if not self.nr_document and self.document_type == 'gdpr':
            res = True
        return res
    
    def _get_regulation_required_compute(self):
        res = super(Contract, self)._get_regulation_required_compute()
        if self.document_type=='gdpr':
            res = True
        return res
    
    def set_name(self):
        super().set_name()
        for s in self:
            date = datetime.now().date().strftime("%Y-%m-%d")
            if s.document_type == 'gdpr':
                name = _("GDPR %s") % date
                if self.nr_document:
                    name = _("GDPR %s for %s") % (self.nr_document, self.parent_id.nr_document)
                s.name = name
        

class RegulatorNumere(models.Model):
    _inherit = "smart.contract.regulation"
    
    document_type = fields.Selection(selection_add=[("gdpr", "GDPR")], ondelete={'gdpr': 'set default'})

class smartContractTemplate(models.Model):
    _inherit = "smart.contract.template"
    
    document_type = fields.Selection(selection_add=[("gdpr", "GDPR")], ondelete={'gdpr': 'set default'})
    