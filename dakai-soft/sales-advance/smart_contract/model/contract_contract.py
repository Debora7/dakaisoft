# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError
from datetime import datetime, date
import re
#from numbers import ToArabic, ToRoman
from . import numbers

ToArabic, ToRoman = numbers.ToArabic, numbers.ToRoman


class Contract(models.Model):

    _name = "smart.contract"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = _("Smart Contract")


    def _get_date(self):
        return datetime.now().date().strftime("%Y-%m-%d")

    name = fields.Char(string=_("Name"), default=lambda x: x.set_name(), store=True)
    active = fields.Boolean(_("Active"), default=True)
    regulation_id = fields.Many2one("smart.contract.regulation", _("Contract Set"))
    regulation_adition_id = fields.Many2one("smart.contract.regulation", _("Contract Aditional Set"))
    can_change_regulation_adition_id = fields.Boolean(compute="_can_change_regulation_adition_id", default=True)
    partner_id = fields.Many2one(comodel_name="res.partner", string=_("Customer"))
    legal_partner_id = fields.Many2one("res.partner", _("Legal Customer Person"))
    company_id = fields.Many2one(comodel_name='res.company', string=_("Supplier"), required=True, default=1)
    #TODO: In client
    #location_id = fields.Many2one(comodel_name="res.partner", string=_("Locatie client"))
    #stock_location_id = fields.Many2one(comodel_name="stock.location", string=_("Locatie de stoc"))
    #create_date = fields.Date(string=_("Data crearii"), default=_get_date, readonly=True)
    data_intocmirii = fields.Date(string=_("Act Date"), readonly=True, default=fields.Datetime.now().strftime("%Y-%m-%d"))
    date_start = fields.Date(string=_("Start Date"))
    date_end = fields.Date(string=_("End Date"))
    val_triger = fields.Float(compute="_computeValues", string=_("Value for triger o2many"))
    valoare_fixa = fields.Monetary(string=_("Fixed Value"), default=0)
    valoare = fields.Monetary(compute="_computeValues", string=_("Total Value with VAT"), store=True)
    valoare_fara_tva = fields.Monetary(compute="_computeValues", string=_("Value Amount"), store=True)
    currency_id = fields.Many2one(comodel_name="res.currency", string=_("Currency"),
                                  default=lambda x: x.env.user.company_id.currency_id.id, required=True)
    type = fields.Selection([
        ('custommer',_('Custommer')),
        ('supplier',_('Supplier')),
        ('undefined', _("Undefined"))], string=_("Contract Type"), default="custommer", required=True)
    nr_document = fields.Char(string=_("Document no."), compute="set_name", store=True)
    signed_date = fields.Date(string=_("Sign Date"))
    recive_date = fields.Date(string=_("Reception Date"))
    status = fields.Selection(selection=[("draft", _("Draft")),
                                         ('intocmit', _("Prepared")),
                                         ("semnat", _("Signed")),
                                         ("receptionat", _("Received")),
                                         ('anulat', _("Terminated"))], string=_("Status"), default="draft")
    child_ids = fields.One2many(comodel_name="smart.contract", inverse_name="parent_id", string=_("Contract Addendums"))
    parent_id = fields.Many2one(comodel_name="smart.contract", string=_("Contract parent"), ondelete="cascade")
    is_child = fields.Boolean()
    document_type = fields.Selection(selection=[("contract", "Contract"),
                                                ("act", "Contract Addendum")],
                                     string=_("Document Type"), default="contract", required=True)
    template_contract_id = fields.Many2one(comodel_name="smart.contract.template", string=_("Contract Template"))
    elemente_ids = fields.One2many(comodel_name="smart.contract.element", inverse_name="contract_rel_id",
                                   string=_("Articles"), copy=True)

    related_object_ids = fields.One2many("smart.contract.related", "contract_id", string=_("Contract Related Objects"), copy=True)
    sale_ids = fields.One2many("sale.order", "contract_id", _("Sales"))
    purchase_ids = fields.One2many("purchase.order", "contract_id", _("Purchase"))
    variable_count = fields.Integer(_("Variable Count"), compute="_countVariable", help=_("""
        Define 3types of variable, used in text content:
        - ${contract.field} or ${contract.object.method()} global recursive
        - ${attrelation.key.[field_name]} global
        - ${localrelation.key} local
        """))
    related_data_ids = fields.One2many("smart.contract.related.data", "contract_id", _("Related Data"), copy=True)
    execution_ids = fields.One2many("smart.contract.execution", "contract_id", _("Contract Execution"), copy=True)
    user_id = fields.Many2one(comodel_name='res.users', string='Responsible', index=True,
                              default=lambda self: self.env.user)
    create_date_only = fields.Date(string="Creation Date Only", compute='_compute_create_date_only', store=True)

    @api.depends('create_date')
    def _compute_create_date_only(self):
        for record in self:
            if record.create_date:
                record.create_date_only = record.create_date.date()

    def getDatas(self, keys=[], domain=[]):
        self.ensure_one()
        return self.related_data_ids.getDatas(keys=keys, domain=domain)


    def drop(self, obj):
        for s in self:
            s.execution_ids.drop(obj)


    def add(self, obj):
        self.ensure_one()
        self.execution_ids.add(obj, self)

    def _countVariable(self):
        if self.elemente_ids:
            self.env.cr.execute("SELECT text from smart_contract_element where contract_id=%s and text is not NULL", (self.id,))
            elem = self.env.cr.fetchall()
            text = ""
            if elem:
                text = "".join([x[0] for x in elem])
            self.variable_count = len(re.findall(r'\$\{([^}]+)\}', text))
        else:
            self.variable_count = 0

    def serialRacursiveChildElement(self, setElements):
        return [(0, 0, {
                    "name": a.name,
                    "numar": a.numar,
                    "tip": a.tip,
                    "text": a.text,
                    "child_ids": a.child_ids and self.serialRacursiveChildElement(a.child_ids) or [],
                    "attribute_ids": [(0, 0, {
                            "name": adro.name,
                            "data": adro.data,
                            "number": adro.number,
                            "currency_id": adro.currency_id.id,
                            "text": adro.text,
                            }) for adro in a.attribute_ids]
                }) for a in setElements]

    def serialRacursiveChildContract(self, setElements):
        return [(0, 0, {
                    "company_id": a.company_id.id,
                    "document_type": a.document_type,
                    "elemente_ids": self.serialRacursiveChildElement(a.elemente_ids)
                }) for a in setElements]

    def _can_change_regulation_adition_id(self):
        for s in self:
            s.can_change_regulation_adition_id = True
            if any(child.status != 'draft' for child in s.child_ids):
                s.can_change_regulation_adition_id = False

    @api.onchange("regulation_id")
    def change_regulation_id(self):
        self.signed_date = False

    @api.onchange("signed_date")
    def change_signed_date(self):
        last_contract = self.env['smart.contract'].search([('regulation_id', '=', self.regulation_id and self.regulation_id.id or False), ('nr_document', '!=', False)], order='nr_document DESC', limit=1)
        if last_contract.signed_date and self.signed_date and last_contract.signed_date > self.signed_date:
            self.signed_date = False
            raise UserError(_("Signed date must be greater than the last contract sign date!"))

    @api.onchange("template_contract_id")
    def populate_with_data_change(self):
        if not self.template_contract_id:
            return
        self.company_id = self.template_contract_id.company_id.id
        self.document_type = self.template_contract_id.document_type
        self.type = self.template_contract_id.type
        self.regulation_id = self.template_contract_id.regulation_id.id


    def populate_with_data(self):
        self.ensure_one()
        if not self.template_contract_id:
            raise UserError(_("No Template selected"))
        if self.template_contract_id.related_object_ids:
            self.sudo().related_object_ids = [(2, i) for i in self.related_object_ids.mapped("id")] + [(0, 0, {
                    "server_action": ro.server_action.id,
                    "autoexec": ro.autoexec,
                    "racursiv": ro.racursiv,
                    "exec_date": ro.exec_date,
                    "aditional_data_ids": [(0, 0, {
                            "name": adro.name,
                            "data": adro.data,
                            "number": adro.number,
                            "currency_id": adro.currency_id.id,
                            "text": adro.text,
                            }) for adro in ro.aditional_data_ids]
                }) for ro in self.template_contract_id.related_object_ids]
        if self.template_contract_id.child_ids:
            self.sudo().child_ids = [(2, i) for i in self.child_ids.mapped("id")] + self.serialRacursiveChildContract(self.template_contract_id.child_ids)
        if self.template_contract_id.elemente_ids:
            self.sudo().elemente_ids =  [(2, i) for i in self.elemente_ids.mapped("id")] + self.serialRacursiveChildElement(self.template_contract_id.elemente_ids)
        self.sudo().reNumber()

    @api.onchange('parent_id')
    def change_partner(self):
        if self.parent_id:
            self.partner_id = self.parent_id.partner_id.id

    @api.model
    def create(self, values):
        for value in values:
            value['is_child'] = False
        res = super(Contract, self).create(values)
        return res

    @api.model
    def default_get(self, lista):
        res = super(Contract,self).default_get(lista)
        res['partner_id'] = self.env.context.get('partner_id')
        return res

    def intocmire(self):
        if self.parent_id and self.parent_id.nr_document == False:
            raise UserError(_("Please set a number for parent contract first!"))
        self.status = 'intocmit'
        self.data_intocmirii = datetime.now().date().strftime('%Y-%m-%d')


    @api.depends('create_date', 'data_intocmirii', 'document_type')
    def set_name(self):
        for s in self:
            date = datetime.now().date().strftime("%Y-%m-%d")
            if s.document_type == 'contract' and not self.name:
                name = _("Draft Contract %s") % date
                if self.nr_document:
                    name = _("Contract %s") % self.nr_document
                s.name = name
            elif s.document_type == 'act' and not self.name:
                name = _("Draft Contract Addendum %s") % date
                if self.nr_document:
                    name = _("Contract Addendum %s for %s") % (self.nr_document, self.parent_id.nr_document)
                s.name = name
            elif s.document_type == 'gdpr':
                name = _("GDPR %s") % date
                if self.nr_document:
                    name = _("GDPR %s for %s") % (self.nr_document, self.parent_id.nr_document)
                s.name = name
            elif s.document_type == 'notificare':
                name = _("Notification %s") % date
                if self.nr_document:
                    name = _("Notification %s for %s") % (self.nr_document, self.parent_id.nr_document)
                s.name = name

    def set_signed(self):
        if not self.signed_date:
            raise UserError(_("Signed date is not set!"))
        self.status = 'semnat'
        if not self.nr_document:
            self.setNumber()

    def set_recive(self):
        self.status = 'receptionat'

    def cancel(self):
        self.status = 'anulat'
        self.sale_ids.action_cancel()

    @api.depends("sale_ids", "valoare_fixa", "purchase_ids")
    def _computeValues(self):
        def computeCurrency(put, out, value, obj, company=None, date=None):
            if not date:
                date = fields.Datetime.now()
            if not company:
                company = obj.company_id
            return put._convert(value, out, company, date)

        def getTax(obj):
            company_id = obj.env.user.company_id.id
            IrDefault = obj.env['ir.default']
            return obj.env['account.tax'].browse(IrDefault._get('product.template', 'taxes_id', company_id=company_id))


        for s in self:
            if s.sale_ids and s.valoare_fixa==0:
                am = [(
                        computeCurrency(i.currency_id, s.currency_id, i.amount_total, i, company=i.company_id, date=i.date_order),
                        computeCurrency(i.currency_id, s.currency_id, i.amount_untaxed, i,  company=i.company_id, date=i.date_order),
                        computeCurrency(i.currency_id, s.currency_id, i.amount_tax, i, company=i.company_id, date=i.date_order)
                        ) for i in s.sale_ids]
                valoare = sum(map(lambda x:x[0], am))
                valoare_no_vat = sum(map(lambda x:x[1],am))
                s.valoare = valoare if valoare!=s.valoare else s.valoare
                s.valoare_fara_tva = valoare_no_vat if valoare_no_vat!=s.valoare_fara_tva else s.valoare_fara_tva
                s.val_triger = s.valoare
            elif s.purchase_ids:
                am = [(
                    computeCurrency(i.currency_id, s.currency_id, i.amount_total, i, company=i.company_id,
                                    date=i.date_order),
                    computeCurrency(i.currency_id, s.currency_id, i.amount_untaxed, i, company=i.company_id,
                                    date=i.date_order),
                    computeCurrency(i.currency_id, s.currency_id, i.amount_tax, i, company=i.company_id,
                                    date=i.date_order)
                ) for i in s.purchase_ids]
                valoare = sum(map(lambda x: x[0], am))
                valoare_no_vat = sum(map(lambda x: x[1], am))
                s.valoare = valoare if valoare != s.valoare else s.valoare
                s.valoare_fara_tva = valoare_no_vat if valoare_no_vat != s.valoare_fara_tva else s.valoare_fara_tva
                s.val_triger = s.valoare
            else:
                tax = getTax(s).compute_all(s.valoare_fixa)
                s.valoare = tax["total_included"]
                s.valoare_fara_tva = tax["total_excluded"]
                s.val_triger = s.valoare


    #========================  Controls

    def setNumber(self):
        self.ensure_one()
        if self.document_type == 'contract':
            self.nr_document = self.regulation_id.getNext()
        elif self.document_type == 'act':
            if not self.parent_id.regulation_adition_id:
                self.nr_document = len(self.parent_id.child_ids.filtered(lambda x:x.status not in ['draft','anulat']))
            else:
                self.nr_document = self.parent_id.regulation_adition_id.getNext()
        self.set_name()

        if self.sale_ids:
            for s in self.sale_ids.filtered(lambda x: x.state in ['draft','sent']):
                s.action_confirm()
        return True


    def ParseVariable(self):
        for s in self:
            s.elemente_ids.parseAll()


    def reNumber(self):
        return self.elemente_ids.reNumber()


    def web_edit(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "Results of the Survey",
            'target': 'self',
            'url': "/smart_contract/%(request_id)s" % {'request_id': self.id}
        }



    def write(self, values):
        res = super(Contract, self).write(values)
        if values.get("elemente_ids", None):
            self.updateContractElem(self.elemente_ids, self.id)
        return res


    def updateContractElem(self, o, cid):
        for i in o:
            i.contract_id = cid
            if i.child_ids:
                self.updateContractElem(i.child_ids, cid)


    def postMail(self, *args, **kwargs):
        if kwargs.get('error'):
            kwargs['body'] = tools.ustr(kwargs.get('error'))
        for s in self:
            partner = [self.create_uid.partner_id.id, self.write_uid.partner_id.id]
            kwargs['partner_ids'] = partner
            kwargs['subtype'] = 'email'
            s.message_post(**kwargs)



    def _get_report_base_filename(self):
        self.ensure_one()
        name = None
        if self.document_type == 'contract' and not self.nr_document:
            name = _('Contract %s') % (self.name,)
        elif self.document_type == 'act' and not self.nr_document:
            name = _('Contract Addendum %s la Contract %s') % (self.name, self.parent_id.nr_document)
        elif self.document_type == 'contract' and self.nr_document:
            name = _('Contract %s') % (self.nr_document,)
        elif self.document_type == 'act' and self.nr_document:
            name = _('Contract Addendum %s for %s') % (self.nr_document, self.parent_id.nr_document)
        else:
            name = "Contract " + self.name
        return name

    show_regulation = fields.Boolean(_("Show Regulation Serie"), compute="_regulation_show")


    def _compute_show_regulation(self):
        res = False
        if not self.nr_document and self.document_type == 'contract':
            res = True
        return res

    @api.depends('nr_document', 'document_type')
    def _regulation_show(self):
        res = self._compute_show_regulation()
        self.show_regulation = res

    required_regulation = fields.Boolean(_("Require regulation"), compute="_get_regulation_required")


    def _get_regulation_required_compute(self):
        res = False
        if self.document_type=='contract':
            res = True
        return res

    @api.depends('document_type')
    def _get_regulation_required(self):
        res = self._get_regulation_required_compute()
        self.required_regulation = res

    def action_add_attachment(self):
        pdf = self.env['ir.actions.report']._render_qweb_pdf("smart_contract.smart_contract_pdf_report", self.id)
        b64_pdf = base64.b64encode(pdf[0])
        name = f'{self.name}.pdf'

        for sale_id in self.sale_ids:
            existing_attachment = self.env['ir.attachment'].search([
                ('res_model', '=', sale_id._name),
                ('res_id', '=', sale_id.id),
                ('name', '=', name)
            ], limit=1)

            if not existing_attachment:
                self.env['ir.attachment'].create({
                    'name': name,
                    'type': 'binary',
                    'datas': b64_pdf,
                    'store_fname': name,
                    'res_model': sale_id._name,
                    'res_id': sale_id.id,
                    'mimetype': 'application/x-pdf'
                })

        return True


class ContractElement(models.Model):

    _name = "smart.contract.element"
    _description = _("Smart Contract element")
    _order = "order ASC"

    name = fields.Char(string=_("Name"))
    numar = fields.Char(string=_("Number"))
    tip = fields.Selection([("capitol", _("Chapter")), ("articol", _("Article")), ("alineat", _("Paragraph"))], string=_("Type"))
    text = fields.Html(string=_("Content"))
    cleartext = fields.Html(string=_("Content"), compute="_reportClearText")
    child_ids = fields.One2many(comodel_name="smart.contract.element",
                                inverse_name="parent_id", string=_("Childs"))
    parent_id = fields.Many2one(comodel_name="smart.contract.element", string=_("Parent"), ondelete="cascade")
    contract_rel_id = fields.Many2one(comodel_name="smart.contract", string=_("Contract"), ondelete="cascade")
    contract_id = fields.Many2one(comodel_name="smart.contract", string=_("Contract"), ondelete="cascade")
    attribute_ids = fields.One2many("smart.contract.related.data", "element_id", _("Element Attributes"))
    order = fields.Integer(string=_('Order'))


    def _reportClearText(self):
        for s in self:
            text = s.text
            if text:
                groups = re.findall(r'\$\{([^}]+)\}', text)
                for x in groups:
                    iText = "${%s}" % (x,)
                    rText = re.sub(r'(.*)', '_', iText)
                    text = text.replace(iText, rText)
            s.cleartext = text


    def parseAll(self):
        for s in self:
            s.parseRacursive()

    def parseRacursive(self):
        if self.text:
            self.text = self._parse()
        if self.child_ids:
            for s in self.child_ids:
                s.parseRacursive()

    def _parse(self):
        """
        Define 3types of variable, used in text content:
        - ${contract.field} or ${contract.object.method()} global recursive
        - ${attrelation.key} global
        - ${localrelation.key} local
        """
        lang = self.env['res.lang'].search([('code','=',self.env.user.lang)])
        groups = re.findall(r'\$\{([^}]+)\}', self.text)
        peers = []

        def obj2string(res):
            if isinstance(res, datetime):
                return res.strftime(lang.date_format)
            elif isinstance(res, date):
                return res.strftime(lang.date_format)
            elif isinstance(res, (int, float)):
                return str(res)
            elif isinstance(res, models.Model):
                return res.display_name
            return res

        for g in groups:
            peers.append((g, self._getValueParsed(g)))
        text = self.text
        for p in peers:
            #de formatat inputul diferit de str.
            search, replace = "${%s}" % (p[0],), p[1]
            try:
                text = text.replace(search, obj2string(replace))
            except Exception as e:
                alert = tools.ustr(e)
                raise UserError("%s\n%s - %s" % (alert, search, obj2string(replace)))
        return text

    def _getValueParsed(self, fieldData):
        fieldsData = fieldData.split(".")
        if fieldsData[0] == 'contract' and fieldsData[-1][-2:]=='()':
            ctr = self.contract_id
            for p in fieldsData[1:]:
                if fieldsData[-1]==p:
                    f = p.replace("()","")
                    func = getattr(ctr, f, None)
                    if func:
                        ctr = func()
                    break
                ctr = getattr(ctr, p, None)
                if not ctr:
                    break
            return ctr and ctr or "${%s}" % (fieldData,)
        elif fieldsData[0] == 'contract':
            ctr = self.contract_id
            for p in fieldsData[1:]:
                ctr = getattr(ctr, p, None)
                if not ctr:
                    break
            return ctr and ctr or "${%s}" % (fieldData,)
        elif fieldsData[0] == 'localrelation' and len(fieldsData)<3:
            return "${%s}" % (fieldData,)
        elif fieldsData[0] == 'localrelation':
            return getattr(self.attribute_ids.getData(fieldsData[1]),fieldsData[2], "${%s}" % (fieldData,))
        elif fieldsData[0] == 'attrelation' and len(fieldsData)<3:
            return "${%s}" % (fieldData,)
        elif fieldsData[0] == 'attrelation':
            return getattr(self.contract_id.related_data_ids.getData(fieldsData[1]),fieldsData[2], "${%s}" % (fieldData,))


    def CapCr(self):
        for i in range(1000):
            rmn = ToRoman(i+1).roman
            yield _("Cap.%s") % (rmn,)

    def ArtCr(self):
        for i in range(1000):
            yield _("Art.%s") % (i+1,)

    def AlinCr(self):
        for i in range(ord('a'), ord('z')+1):
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
        res = super(ContractElement, self).write(values)
        return res

    @api.model
    def default_get(self, fields=["tip", "parent_id", "contract_id"]):
        res = super(ContractElement, self).default_get(fields)
        setlist = ['contract', 'capitol', 'articol', 'alineat']
        if self.env.context.get('type', None):
            nextItem = setlist.index(self.env.context.get('type', None))
            res["tip"] = len(setlist)==nextItem+1 and setlist[-1] or setlist[nextItem+1]
        if self.env.context.get("element", None):
            res["parent_id"] = self.env.context.get("element")
        return res

    @api.model
    def create(self, values):
        if 'order' not in values:
            tip = values.get('tip')
            if values.get('parent_id', None):
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
        res = super(ContractElement, self).create(values)
        if res.parent_id:
            res.contract_id = res.parent_id.contract_id.id
        elif res.contract_rel_id:
            res.contract_id = res.contract_rel_id.id
        res.contract_id.reNumber()
        return res


class RegulatorNumere(models.Model):
    _name = "smart.contract.regulation"
    _description = _("Contract regulation numbers and series")

    name = fields.Char(_("Set name"))
    serial_id = fields.Many2one("ir.sequence", _("Serial Sequence"), required=True)
    sequence_current = fields.Char(_("Current Sequence"))
    document_type = fields.Selection(selection=[("contract", "Contract"),
                                                ("act", "Contract Addendum")],
                                     string=_("Document type"), default="contract")


    def getNext(self):
        self.ensure_one()
        if not self.serial_id:
            raise UserError(_("Please set a serial sequence on your contract set!"))
        number = self.serial_id.next_by_id()
        self.sequence_current = number
        return number