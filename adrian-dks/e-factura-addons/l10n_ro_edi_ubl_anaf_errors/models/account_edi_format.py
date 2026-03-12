from odoo import api, fields, models, _
from odoo.exceptions import UserError
import io
import zipfile
from lxml import etree
from datetime import timedelta, datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class AccountEdiXmlCIUSRO(models.Model):
    _inherit = "account.edi.format"

    def l10n_ro_get_idDescarcare(self, invoice):
        edi_format = len(self)==1 and self or invoice.journal_id.edi_format_ids
        edi_doc = invoice._get_edi_document(edi_format)
        start = str(edi_doc.create_date - timedelta(seconds=60))
        end = str(edi_doc.create_date - timedelta(days=2))
        res = invoice.company_id._l10n_ro_get_anaf_efactura_messages(start=start, end=end, filtru="E")
        res += invoice.company_id._l10n_ro_get_anaf_efactura_messages(start=start, end=end, filtru="T")
        res = [rs for rs in res if rs.get("id_solicitare") == invoice.l10n_ro_edi_transaction]
        if not res:
            return None
        edi_doc.l10n_ro_edi_download = res[0].get('id')
        return edi_doc.l10n_ro_edi_download

    def l10n_ro_download_zip_anaf(self, invoice, anaf_config=False):
        if not anaf_config or (type(anaf_config) is dict):
            anaf_config = invoice.sudo().company_id._l10n_ro_get_anaf_sync(scope="e-factura")
        if not anaf_config:
            raise UserError(
                _("The ANAF configuration is not set. Please set it and try again.")
            )
        if not invoice.l10n_ro_edi_download:
            self.l10n_ro_get_idDescarcare(invoice)

        params = {"id": invoice.l10n_ro_edi_download}
        response, status_code = anaf_config._l10n_ro_einvoice_call(
            "/descarcare", params, method="GET"
        )
        eroare = ""
        if type(response) == dict:
            eroare = response.get("eroare", "")
        if status_code == "400":
            eroare = response.get("message")
        elif status_code == 200 and type(response) == dict:
            eroare = response.get("eroare")
        if eroare:
            return {
                'success': False,
                'error': eroare
            }
        return {
            'success': True,
            'zip_content': response
        }
    
    def l10n_ro_check_anaf_error_xml(self, zip_content, l10n_ro_edi_transaction):
        zip_ref = zipfile.ZipFile(io.BytesIO(zip_content))
        err_file = [f for f in zip_ref.namelist() if f"{l10n_ro_edi_transaction}.xml" == f]
        success_check = True
        err_msg = False
        if err_file:
            err_cont = zip_ref.read(err_file[0])
            edi_format_cius = self.env["account.edi.format"].search(
                [("code", "=", "cius_ro")]
            )
            decode_xml = edi_format_cius._decode_xml(err_file[0], err_cont)
            if decode_xml:
                tree = decode_xml[0]['xml_tree']
            error_tag = 'Error'
            err_msg = 'Erori validare ANAF:<br/>'
            for index, err in enumerate(tree.findall('./{*}' + error_tag)):
                err_msg += f"{err.attrib.get('errorMessage')}<br/>"
                success_check = False
        return {
            'success': success_check,
            'error': err_msg
        }
            
    def _l10n_ro_post_invoice_step_2(self, invoice, attachment):
        res = super(AccountEdiXmlCIUSRO, self)._l10n_ro_post_invoice_step_2(invoice, attachment)
        if res.get('blocking_level', False) == 'error' or res.get('state', None)=='error':
            id_descarcare = res.get("message", {}).get("id_descarcare", None)
            invoice.write({
                "l10n_ro_edi_download":id_descarcare,
                })
            zip_response = self.l10n_ro_download_zip_anaf(invoice)
            zip_info = self.l10n_ro_check_anaf_error_xml(zip_response.get('zip_content'), invoice.l10n_ro_edi_transaction)
            invoice.message_post(body=zip_info.get("error"))
            edi_format = len(self)==1 and self or invoice.journal_id.edi_format_ids
            edi_doc = invoice._get_edi_document(edi_format)
            if edi_doc and edi_doc.l10n_ro_reload_einvoice == True:
                res["blocking_level"] = "error"
                invoice.write({
                    "l10n_ro_edi_transaction": None,
                    })
        return res


    #========================= To be merged
    def _l10n_ro_anaf_call(self, func, anaf_config, params, data=None, method="POST"):

        content, status_code = anaf_config._l10n_ro_einvoice_call(
            func, params, data, method
        )
        if status_code == 400:
            error = _("Error %s") % status_code
            return {
                "success": False,
                "error": error,
                "blocking_level": "error",
                "message": {'status_code': status_code},
                "state": "error",
                }
        elif status_code != 200:
            return {
                "success": False,
                "error": _("Access Error"),
                "blocking_level": "warning",
                "message": {'status_code': status_code},
                "state": "error",
            }

        doc = etree.fromstring(content)

        namespaces = {
            "step1": "mfp:anaf:dgti:spv:respUploadFisier:v1",
            "step2": "mfp:anaf:dgti:efactura:stareMesajFactura:v1",
        }
        errors_step1 = doc.find("step1:Errors", namespaces=namespaces)
        error_message_step1 = (
            errors_step1.get("errorMessage") if errors_step1 is not None else None
        )
        errors_step2 = doc.find("step2:Errors", namespaces=namespaces)
        error_message_step2 = (
            errors_step2.get("errorMessage") if errors_step2 is not None else None
        )
        error_message = error_message_step1 or error_message_step2
        if error_message:
            res = {"success": False, "error": error_message, "blocking_level": "error"}
            if "mesaj in cursul zilei" in error_message:
                res.update({"blocking_level": "warning"})
            return res

        # This is response ok from step 1
        transaction = doc.get("index_incarcare", False)
        if transaction:
            return {
                "success": False,
                "transaction": transaction,
                "blocking_level": "info",
                "error": "The invoice was sent to ANAF, awaiting validation.",
                "message": doc,
                "state": "info",
            }

        # This is response from step 2
        res = {"success": False}
        stare = doc.get("stare", False)
        stari = {
            "in prelucrare": {
                "success": False,
                "blocking_level": "info",
                "in_processing": True,
                "error": "The invoice is in processing at ANAF.",
                "message": doc,
                "state": "info",
            },
            "nok": {
                "success": False,
                "blocking_level": "warning",
                "error": "The invoice was not validated by ANAF.",
                "message": doc,
                "state": "error",
            },
            "ok": {
                "success": True,
                "id_descarcare": doc.get("id_descarcare") or "",
                "message": doc,
                "state": "info",
                },
            "XML cu erori nepreluat de sistem": {
                "success": False,
                "blocking_level": "error",
                "error": "XML cu erori nepreluat de sistem",
                "message": doc,
                "state": "error",
            },
        }
        if stare:
            for key, value in stari.items():
                if key in stare:
                    res.update(value)
                    break
        return res

    # Depreciat
    # Fix compatibility
    # def _post_invoice_edi(self, invoices):
    #     self.ensure_one()
    #     if self.code != "cius_ro":
    #         return super()._post_invoice_edi(invoices)
    #     res = {}
    #     for invoice in invoices:
    #
    #         anaf_config = invoice.company_id._l10n_ro_get_anaf_sync(scope="e-factura")
    #         if not anaf_config:
    #             res[invoice] = {
    #                 "success": True,
    #                 "error": _("ANAF sync manual"),
    #             }
    #             continue
    #
    #         attachment = invoice._get_edi_attachment(self)
    #         if not attachment:
    #             attachment = self._export_cius_ro(invoice)
    #         # Generate PDF report to be embedded in the XML
    #         if invoice.company_id.l10n_ro_edi_cius_embed_pdf:
    #             pdf_report = invoice.company_id.l10n_ro_default_cius_pdf_report
    #             if not pdf_report:
    #                 pdf_report = self.env.ref("account.account_invoices")
    #             self.env["ir.actions.report"]._render_qweb_pdf(
    #                 pdf_report.report_name, invoice.id
    #             )
    #         res[invoice] = {"attachment": attachment, "success": True}
    #
    #         residence = invoice.company_id.l10n_ro_edi_residence
    #         days = (fields.Date.today() - invoice.invoice_date).days
    #         if self.env.context.get("l10n_ro_edi_manual_action") and not invoice.l10n_ro_edi_transaction:
    #             if anaf_config and not invoice.l10n_ro_edi_transaction:
    #                 res[invoice] = self._l10n_ro_post_invoice_step_1(
    #                     invoice, attachment
    #                 )
    #         else:
    #             if not invoice.l10n_ro_edi_transaction:
    #                 if days >= residence:
    #                     res[invoice] = self._l10n_ro_post_invoice_step_1(
    #                         invoice, attachment
    #                     )
    #                 else:
    #                     res[invoice] = {
    #                         "success": False,
    #                         "error": _("The invoice is not older than %s days")
    #                         % residence,
    #                     }
    #
    #             else:
    #                 res[invoice] = self._l10n_ro_post_invoice_step_2(
    #                     invoice, attachment
    #                 )
    #         if res[invoice].get("error", False):
    #             invoice.message_post(body=res[invoice]["error"])
    #             # Create activity if process is stoped with an error blocking level
    #             if res[invoice].get("blocking_level") == "error":
    #                 body = (
    #                     _(
    #                         "The invoice was not send or validated by ANAF."
    #                         "\n\nError:"
    #                         "\n<p>%s</p>"
    #                     )
    #                     % res[invoice]["error"]
    #                 )
    #
    #                 invoice.activity_schedule(
    #                     "mail.mail_activity_data_warning",
    #                     summary=_("The invoice was not send or validated by ANAF"),
    #                     note=body,
    #                     user_id=invoice.invoice_user_id.id,
    #                 )
    #         # If you have ANAF sync configured, but you don't have a transaction
    #         # number, then the invoice is marked as not sent to ANAF
    #         if (
    #             anaf_config
    #             and not invoice.l10n_ro_edi_transaction
    #             and not res.get("transaction")
    #         ):
    #             res["success"] = False
    #     return res
            
            
