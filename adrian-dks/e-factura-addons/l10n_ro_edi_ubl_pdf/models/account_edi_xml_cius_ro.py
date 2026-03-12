from odoo import models
from base64 import b64encode, b64decode
import requests


class AccountUblCiusRo(models.Model):
    _inherit = "account.edi.xml.cius_ro"


    def _import_invoice(self, journal, filename, tree, existing_invoice=None):
        invoice = super(AccountUblCiusRo, self)._import_invoice(journal, filename, tree, existing_invoice=existing_invoice)
        additional_docs = tree.findall('./{*}AdditionalDocumentReference')
        if len(additional_docs) == 0:
            res = self.l10n_ro_renderAnafPdf(invoice)
            if not res:
                pdf = self.env['ir.actions.report'].sudo()._render_qweb_pdf('account.account_invoices_without_payment', [invoice.id])
                b64_pdf = b64encode(pdf[0])
                self.l10n_ro_addPDF_from_att(invoice, b64_pdf)
        return invoice



    def l10n_ro_renderAnafPdf(self, invoice):
        attachement = invoice.attachment_ids.filtered(lambda x: f"{invoice.l10n_ro_edi_transaction}.xml" in x.name)
        if not attachement:
            return False
        headers = {'Content-Type': 'text/plain'}
        xml = b64decode(attachement.datas)
        val1 = 'refund' in invoice.move_type and "FCN" or "FACT1"
        val2 = "DA"
        try:
            res = requests.post(f'https://webservicesp.anaf.ro/prod/FCTEL/rest/transformare/{val1}/{val2}', data=xml, headers=headers)
            if "The requested URL was rejected" in res.text:
                xml = xml.replace(b'xsi:schemaLocation="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2 ../../UBL-2.1(1)/xsd/maindoc/UBLInvoice-2.1.xsd"',"")
                res = requests.post(f'https://webservicesp.anaf.ro/prod/FCTEL/rest/transformare/{val1}/{val2}', data=xml, headers=headers)
        except Exception as e:
            return False
        else:
            return self.l10n_ro_addPDF_from_att(invoice, b64encode(res.content))

    def l10n_ro_addPDF_from_att(self, invoice, pdf):
        attachments = self.env['ir.attachment'].create({
                'name': invoice.ref,
                'res_id': invoice.id,
                'res_model': 'account.move',
                'datas': pdf + b'=' * (len(pdf) % 3),  # Fix incorrect padding
                'type': 'binary',
                'mimetype': 'application/pdf',
            })
        if attachments:
            invoice.with_context(no_new_invoice=True).message_post(attachment_ids=attachments.ids)
        return True

