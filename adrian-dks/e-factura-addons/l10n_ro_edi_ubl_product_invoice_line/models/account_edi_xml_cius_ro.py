from odoo import api, fields, models


class AccountEdiXmlUBL(models.Model):
    _inherit = "account.edi.xml.cius_ro"
    
    def _l10n_ro_search_iban(self, iban, bank, partner):
        bnk = self.env['res.partner.bank']
        bnk_name = self.env['res.bank']
        bank_nbr_id = bnk.search([('acc_number', '=', iban)])
        if not bank_nbr_id and iban:
            bank_nbr_id = bnk.create([{
                'bank_id': bnk_name.search([('name','=',bank)]).id or None,
                'acc_number': iban,
                'partner_id': partner.id,
                'l10n_ro_print_report': True,
                }])
        return bank_nbr_id
    
    def _l10n_ro_import_retrieve_partner_bank(self, tree, invoice):
        iban = tree.find('./{*}PaymentMeans/{*}PayeeFinancialAccount/{*}ID')
        bank = tree.find('./{*}PaymentMeans/{*}PayeeFinancialAccount/{*}Name')
        if iban is not None:
            invoice.partner_bank_id = self._l10n_ro_search_iban(iban.text, (bank is not None and bank.text or ""), invoice.partner_id).id
    
    def _import_fill_invoice_form(self, journal, tree, invoice, qty_factor):
        res = super(AccountEdiXmlUBL, self)._import_fill_invoice_form(journal, tree, invoice, qty_factor)
        if journal.type == 'purchase':
            self._l10n_ro_import_retrieve_partner_bank(tree, invoice)
        return res
            
    # def _import_retrieve_and_fill_partner(self, invoice, name, phone, mail, vat, country_code=False, street=False, street2=False, city=False, zip_code=False):
    #     super(AccountEdiXmlUBL, self)._import_retrieve_and_fill_partner(invoice, name, phone, mail, vat, country_code=country_code, street=street, street2=street2, city=city, zip_code=zip_code)
    #     if not invoice.partner_id:
    #         dict_partner = {
    #             'is_company': True,
    #             'name': name or vat,
    #             'vat': vat,
    #             'email': mail,
    #             'phone': phone,
    #             'country_id': self.env['res.country'].search([('code','=',country_code)], limit=1).id or None
    #             }
    #         new_partner = self.env['res.partner'].create(dict_partner).id
    #         new_partner.ro_vat_change()
    #         invoice.partner_id = new_partner

    
    def _import_fill_invoice_line_form(self, journal, tree, invoice, invoice_line, qty_factor):
        res = super(AccountEdiXmlUBL, self)._import_fill_invoice_line_form(journal, tree, invoice, invoice_line, qty_factor)
        tax_nodes = tree.findall('.//{*}Item/{*}ClassifiedTaxCategory/{*}ID')
        if len(tax_nodes)==1:
            if tax_nodes[0].text in ['O','E','Z']:
                tax = self.env['account.tax'].search([
                    ('amount','=','0'), 
                    ('type_tax_use','=', journal.type),
                    ('amount_type','=','percent')
                    ], limit=1)
                invoice_line.tax_ids = [tax.id]
        return res
        
    def _import_fill_invoice_line_values(self, tree, xpath_dict, invoice_line, qty_factor):
        # Description
        description_node = tree.find('./{*}Item/{*}Description')
        name_node = tree.find('./{*}Item/{*}Name')
        if description_node is not None and name_node is not None:
            name = " - ".join([description_node.text, name_node.text])
            invoice_line.name = name
        res = super(AccountEdiXmlUBL, self)._import_fill_invoice_line_values(tree, xpath_dict, invoice_line, qty_factor)
        if not invoice_line.product_id and invoice_line.move_id.journal_id.type == 'purchase':
            product = self._import_retrieve_info_from_map(tree, self._import_retrieve_product_map(invoice_line.company_id), invoice_line.move_id.partner_id)
            if product:
                self._l10n_ro_line_product(invoice_line, product)
        return res

    def _l10n_ro_line_product(self, invoice_line, product):
        if product:
            invoice_line.product_id = product.id
            if product.categ_id.property_valuation == 'real_time':
                acc = product._get_product_accounts()
                invoice_line.account_id = acc.get('stock_valuation')

    def _import_retrieve_product_map(self, company):
        checkNode = lambda x: x is not None and x.text or None

        def with_suplier_name(tree, extra_domain):
            name_node = tree.find('./{*}Item/{*}Name')
            description_node = tree.find('./{*}Item/{*}Description')

            if all([name_node is None, description_node is None]):
                return None

            if not any([checkNode(name_node), checkNode(description_node)]):
                return None

            return self.env['product.product'].search(extra_domain + [
                ('seller_ids.product_name', 'in', [checkNode(name_node), checkNode(description_node)])
                ], limit=1)

        def with_suplier_code(tree, extra_domain):
            name_node = tree.find('./{*}Item/{*}Name')
            description_node = tree.find('./{*}Item/{*}Description')
            default_code_node = tree.find('./{*}Item/{*}SellersItemIdentification/{*}ID')

            if all([
                    default_code_node is None,
                    description_node is None,
                    name_node is None,
                    ]):
                return None
            in_list = []

            if checkNode(default_code_node):
                in_list += [checkNode(default_code_node)]

            if checkNode(description_node):
                in_list += [checkNode(description_node)]

            if checkNode(name_node):
                in_list += [checkNode(name_node)]

            if not in_list:
                return None
            domain = extra_domain + [
                        ('seller_ids.product_code', 'in', [checkNode(default_code_node), checkNode(description_node), checkNode(name_node)])
                    ]
            records = self.env['product.product'].search(domain, limit=1)
            return records
        
        import_method_map = {
            10: lambda tree, partner: with_suplier_code(tree, [('seller_ids.company_id', '=', company.id), ('seller_ids.partner_id','=',partner.id)]),
            30: lambda tree, partner: with_suplier_name(tree, [('seller_ids.company_id', '=', company.id), ('seller_ids.partner_id','=',partner.id)])
            }
        return import_method_map
    
    def _import_retrieve_info_from_map(self, tree, import_method_map, partner):
        for key in sorted(import_method_map.keys()):
            record = import_method_map[key](tree, partner)
            if record:
                return record

        return None
