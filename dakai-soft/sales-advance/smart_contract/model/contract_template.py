# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from . import numbers

ToArabic, ToRoman = numbers.ToArabic, numbers.ToRoman



class TemplateContract(models.Model):

    _name = "smart.contract.template"
    _description = _("Smart contract template")


    name = fields.Char(string=_("Name"))
    regulation_id = fields.Many2one("smart.contract.regulation", _("Contract Set"))
    customer_id = fields.Many2one(comodel_name="res.partner", string=_("Custommer"))
    company_id = fields.Many2one(comodel_name='res.company', string=_("Supplier"), required=True, default=1)
    child_ids = fields.One2many(comodel_name="smart.contract.template", inverse_name="parent_id",
                                string=_("Contract Addendums"), copy=True)
    parent_id = fields.Many2one(comodel_name="smart.contract.template", string=_("Contract Parent"), ondelete="cascade")
    document_type = fields.Selection(selection=[("contract", _("Contract")), ("act", _("Contract Addendum"))],
                                     string=_("Document Type"), default="contract", required=True)
    elemente_ids = fields.One2many(comodel_name="smart.contract.template.element",
                                   inverse_name="template_id", string=_("Articles"), copy=True)
    # stages_ids = fields.Many2many(comodel_name="project.stage", string=_("Etape"))
    related_object_ids = fields.One2many("smart.contract.related.template", "contract_id", string=_("Contract Related Objects"), copy=True)
    type = fields.Selection([
        ('custommer',_('Custommer')),
        ('supplier',_('Supplier')),
        ('undefined', _("Undefined"))], string=_("Contract Type"), default="custommer")

    def reNumber(self):
        return self.elemente_ids.reNumber()

class TemplateContractElement(models.Model):

    _name = "smart.contract.template.element"
    _description = _("Smart Contract Template element")


    name = fields.Char(string=_("Name"))
    numar = fields.Char(string=_("Number"), compute="set_number_by_order", store=True)
    tip = fields.Selection([("capitol", _("Chapter")), ("articol", _("Article")), ("alineat", _("Paragraph"))], string=_("Type"))
    text = fields.Html(string=_("Content"))
    child_ids = fields.One2many(comodel_name="smart.contract.template.element",
                                inverse_name="parent_id", string=_("SubElements"), copy=True)
    parent_id = fields.Many2one(comodel_name="smart.contract.template.element", string=_("Parent"), ondelete="cascade")
    template_id = fields.Many2one(comodel_name="smart.contract.template", string=_("Template"), ondelete="cascade")
    attribute_ids = fields.One2many("smart.contract.related.template.data", "element_id", _("Element Attributes"))
    order = fields.Integer(string=_('Order'))
 

    def CapCr(self):
        for i in range(1000):
            rmn = ToRoman(i + 1).roman
            yield _("Cap.%s") % (rmn,)

    def ArtCr(self):
        for i in range(1000):
            yield _("Art.%s") % (i + 1,)

    def AlinCr(self):
        for i in range(ord('a'), ord('z') + 1):
            yield _("Alin.%s") % chr(i)

    def reNumber(self, art=None):
        x = 1
        cap = self.CapCr()
        art = art or self.ArtCr()
        alin = self.AlinCr()

        def getNext(tip):
            if tip == 'capitol':
                return next(cap)
            elif tip == 'articol':
                return next(art)
            elif tip == 'alineat':
                return next(alin)

        for s in self:
            s.order = x
            s.numar = getNext(s.tip)
            x += 1
            if s.child_ids:
                s.child_ids.reNumber(art=art)
    
    def unlink(self):
        for s in self:
            s.child_ids.unlink()
        return models.Model.unlink(self)

    
    def write(self, values):
        if values.get('child_ids', None):
            i = 0
            for index, e in enumerate(values.get('child_ids')):
                i += 1
                if(isinstance(values["child_ids"][index][2], dict)):
                    values["child_ids"][index][2]["order"] = i
                elif e[0]==4:
                    values["child_ids"][index]=[1, e[1], {"order": i}]
                elif e[0] in (2, 3, 5, 6):
                    i -= 1
        res = super(TemplateContractElement, self).write(values)
        return res

    @api.model
    def create(self, values):
        if 'order' not in values:
            tip = values.get('tip')
            if 'parent_id' in values and values.get('parent_id', None):
                parent_id = values.get('parent_id')
                parent = self.browse(parent_id)
                if not parent.child_ids:
                    values['order'] = 1
                else:
                    values['order'] = len(parent.child_ids) + 1
            else:
                x = self.search([('tip', '=', tip)])
                if not x:
                    values['order'] = 1
                else:
                    values['order'] = len(x) + 1
        res = super(TemplateContractElement, self).create(values)
        res.template_id.reNumber()
        return res
    
    
    @api.model
    def default_get(self, fields=["tip", "parent_id", "contract_id"]):
        res = super(TemplateContractElement, self).default_get(fields)
        setlist = ['contract', 'capitol', 'articol', 'alineat']
        if self.env.context.get('type', None):
            nextItem = setlist.index(self.env.context.get('type', None))
            res["tip"] = len(setlist)==nextItem+1 and setlist[-1] or setlist[nextItem+1]
        if self.env.context.get("element", None):
            res["parent_id"] = self.env.context.get("element")
        return res
