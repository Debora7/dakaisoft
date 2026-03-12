from odoo import models, fields, _


class DocRelated(models.Model):
    
    _name = "smart.contract.related.template"
    _description = _("Smart Contract template related")

    
    res_model = fields.Many2one("ir.model", _("Model Data"))
    res_id = fields.Integer(_("Model ID"))
    contract_id = fields.Many2one("smart.contract.template", _("Contract Id"))
    name = fields.Many2one("smart.contract.template.element", _("Element Contract"))
    server_action = fields.Many2one("ir.actions.server", _("Server Action"), required=True)
    autoexec = fields.Boolean(_("Auto Execution"))
    racursiv = fields.Boolean(_("Racursive Execution"))
    exec_date = fields.Datetime(_("Execution Date"))
    aditional_data_ids = fields.One2many("smart.contract.related.template.data", "related_id", _("Data Set"))


class DataSet(models.Model):
    _name = "smart.contract.related.template.data"
    _description = _("Smart Contract template related data")

    
    name = fields.Char("Key")
    related_id = fields.Many2one("smart.contract.related.template", _("Related"))
    element_id = fields.Many2one("smart.contract.template.element", _("Element"))
    data = fields.Datetime("Date")
    number = fields.Monetary("Value")
    currency_id = fields.Many2one("res.currency", _("Currency"))
    text = fields.Text(_("Text"))
