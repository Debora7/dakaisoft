from odoo import api, models, fields, _
from odoo.exceptions import UserError


class Execution(models.Model):
    _name = "smart.contract.execution"
    _description = "Contract Execution"
    
    def _getSourceReference(self):
        return [(i.model, i.name) for i in self.env["ir.model"].search([])]
    
    name = fields.Reference(selection="_getSourceReference", string=_("Source Document"), store=True)
    contract_id = fields.Many2one("smart.contract", _("Contract"), ondelete="cascade")
    res_model = fields.Char(_("Res Model"))
    res_id = fields.Integer(_("Res ID"))
    
    def check(self, res_model, res_id):
        self.env.cr.execute("SELECT * from smart_contract_execution where res_model=%s and res_id=%s", (res_model, res_id))
        exist = self.env.cr.fetchall()
        prezent = False
        try:
            self.env.cr.execute("SELECT count(*) as c from smart_contract_execution where res_model=%s and res_id=%s", (res_model, res_id))
        except:
            prezent=False
        else:
            real = self.env.cr.fetchone()
            if real:
                prezent = True
            else:
                prezent=False
        return prezent and len(exist)>0 or False
    
    
    def drop(self, obj):
        for o in obj:
            res_model, res_id = o._name, o.id
            self.filtered(lambda x: x.res_model==res_model and x.res_id == res_id).unlink()
    
    
    def add(self, obj, contract):
        dataSet = self
        for o in obj:
            dataSet |= self.create({
                    "name": "%s,%s" % (o._name, o.id),
                    "res_model": o._name,
                    "res_id": o.id,
                    "contract_id": contract.id,
                    })
        return dataSet
    
    @api.model
    def create(self, values):
        res_model, res_id = values.get('res_model', None), values.get('res_id', None)
        if not all([res_model, res_id]):
            res_model, res_id = values.get('name', ",").split(",")
        if res_model and res_id:
            if self.check(res_model, res_id):
                return UserError(_("Object Reference is required"))
        values["res_model"] = res_model
        values["res_id"] = res_id
        res = super(Execution, self).create(values)
        return res 
    
    
    def write(self, values):
        if values.get("name",None):
            res_model, res_id = values.get('name').split(",")
            if self.check(res_model, res_id):
                return UserError(_("Object Reference is required"))
            values["res_model"] = res_model
            values["res_id"] = res_id
        res = super(Execution, self).write(values)
        return res 
    