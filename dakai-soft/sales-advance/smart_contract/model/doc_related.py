from odoo import api, models, fields, _
from odoo.exceptions import UserError
from datetime import datetime


class DocRelated(models.Model):
    
    _name = "smart.contract.related"
    _description = _("Smart Contract Related Codocuments")

    
    res_model = fields.Many2one("ir.model", _("Model Data"))
    res_id = fields.Integer(_("Model ID"))
    object_id = fields.Reference(selection="_getSourceReference", string=_("Source Document"), store=True)
    contract_id = fields.Many2one("smart.contract", _("Contract"))
    name = fields.Many2one("smart.contract.element", _("Contract Element"))
    server_action = fields.Many2one("ir.actions.server", _("Server Action"), required=True)
    autoexec = fields.Boolean(_("Automatic Execution"))
    racursiv = fields.Boolean(_("Racursive Execution"))
    racursiv_every = fields.Integer(_("Interval Racursive"))
    racursiv_every_type = fields.Selection([('day','Day'), ('month', 'Month'), ('year', 'Year')], _("Recursive Interval Type"), default='day')
    exec_date = fields.Datetime(_("Execution Date"))
    aditional_data_ids = fields.One2many("smart.contract.related.data", "related_id", _("Data Set"))
    
    
    def name_get(self):
        res = []
        for s in self:
            dname = None
            dname = s.name or s.object_id and s.object_id.name
            dname = dname or "New Cron Exec"
            res.append((s.id, dname))
        return res

    def _getSourceReference(self):
        return [(i.model, i.name) for i in self.env["ir.model"].search([])]

    def _getSource(self, model):
        self.env.cr.execute("SELECT res_id from smart_contract_related where res_model=%s", (model.id,))
        used_model_ids = [i[0] for i in self.env.cr.fetchall()]
        return self.env[model.model].search([('id','not in',used_model_ids)]).ids

    
    def getDatas(self, keys=[], domain=[]):
        return self.mapped('aditional_data_ids').getDatas(keys=keys, domain=domain)
    
    
    def getData(self, key, domain=[]):
        return self.mapped('aditional_data_ids').getData(key=key, domain=domain)
    
    @api.onchange("server_action")
    
    def setModel(self):
        res = {}
        if self.server_action:
            model = self.server_action.model_id
            models._logger.error(">>>>>>>>>>>modelmodelmodel>>>>>>>>>>>> %s" % model)
            self.res_model = self.server_action.model_id.id
            src = self._getSource(model)
            models._logger.error(">>>>>>>>>>>srcsrcsrc>>>>>>>>>>>> %s" % src)
            res["value"]={
                "object_id": "%s,%s" % (model.model,len(src)>0 and src[0] or 0),
                'res_model': model.id}
            res["domain"]={
                "object_id":[('id', 'in', src)]
                }
        return res
    
    
    def write(self, values):
        model_id = values.get("server_action", (len(self)>0 and self[0] or self).server_action.id)
        values["res_model"] = self.env["ir.actions.server"].browse(model_id).model_id.id
        if values.get("object_id", None):
            values["res_id"] = values.get("object_id").split(",")[1]
        res = super(DocRelated, self).write(values)
        model = self.mapped("server_action.model_id")
        for s in self:
            if s.object_id:
                if s.object_id._name not in model:
                    raise UserError(_("Action Model and Working model not the same. %s != %s") % (model.mappend(model), s.object_id._name))
        return res

    
    def ExecRelated(self):
        for doc_r in self:
            execution = doc_r.contract_id.execution_ids.filtered(lambda x: x.name._name==doc_r.server_action.model_id.model)
            doc_r.with_context({
                'active_ids': execution and execution.mapped('name.id') or [],
                'contract_id': doc_r.contract_id.id,
                'related': doc_r.id,
                }).server_action.run()
            doc_r.autoexec = False
        

    @api.model
    def RelatedExecute(self):
        self.search([('autoexec','=',True), ('contract_id','!=', False)]).ExecRelated()
#         for doc_r in self.search([('autoexec','=',True), ('contract_id','!=', False)]):
#             execution = doc_r.contract_id.execution_ids.filtered(lambda x: x.name._name==doc_r.server_action.model_id.model)
#             doc_r.with_context({
#                 'active_ids': execution and execution.mapped('name.id') or [],
#                 'contract_id': doc_r.contract_id.id,
#                 'related': doc_r.id,
#                 }).server_action.run()
#             doc_r.autoexec = False

class DataSet(models.Model):
    _name = "smart.contract.related.data"
    _description = _("Smart Contract related documents Data")

    
    name = fields.Char("Key")
    related_id = fields.Many2one("smart.contract.related", _("Related"))
    element_id = fields.Many2one("smart.contract.element", _("Element"))
    contract_id = fields.Many2one("smart.contract", _("Contract"))
    data = fields.Datetime("DateTime")
    number = fields.Monetary("Value Float/Monetary")
    currency_id = fields.Many2one("res.currency", _("Currency"))
    text = fields.Text(_("Text"))

    data_date = fields.Date("Date", compute="_getDate")
    number_int = fields.Integer("Value Integer", compute="_getInt")
    
    
    def setData(self, key, data=None, number=None, currency_id=None, text=None):
        rec = self.filtered(lambda x: x.name==key)
        res = False
        if rec:
            up = {}
            if data:
                up["data"] = data
            if isinstance(number, float):
                up["number"] = number
            if isinstance(currency_id, int):
                up["currency_id"] = currency_id
            if isinstance(text, str):
                up["text"] = text
            res = rec.write(up)
        return res
    
    
    def getData(self, key, domain=[]):
        domain += [('id','in', self.ids)]
        rec = self.search(domain, limit=1).filtered(lambda x: x.name==key)
        return rec
    
    
    def getDatas(self, keys=[], domain=[]):
        #domain += [('id','in',list(self._ids))]
        rec = self.search(domain).filtered(lambda x:x.id in list(self._ids))
        res = {"rec": rec, "domain": domain}
        if keys:
            rec = rec.filtered(lambda x: x.name in keys)
        res.update({x.name: x for x in rec})
        return rec, res
    
    @api.model
    def create(self, values):
        res = super(DataSet, self).create(values)
        res.contract_id = res.related_id.contract_id.id
        return res
    
    
    def _getInt(self):
        for s in self:
            s.number_int = int(s.number)
    
    
    def _getDate(self):
        for s in self:
            if s.data:
                s.data_date = s.data.date()