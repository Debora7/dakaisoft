from odoo import models, fields


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _find_value(self, xpath, xml_element, namespaces=None):
        res = None
        try:
            res = super(AccountEdiFormat, self)._find_value(xpath, xml_element, namespaces=namespaces)
        except Exception as e:
            namespaces = {
                 'qdt': 'urn:oasis:names:specification:ubl:schema:xsd:QualifiedDataTypes-2',
                 'ccts': 'urn:un:unece:uncefact:documentation:2',
                 'udt': 'urn:oasis:names:specification:ubl:schema:xsd:UnqualifiedDataTypes-2',
                 'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
                 'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
                 #None: 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
                 'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
                }
            res = super(AccountEdiFormat, self)._find_value(xpath, xml_element, namespaces=namespaces)
        return res
