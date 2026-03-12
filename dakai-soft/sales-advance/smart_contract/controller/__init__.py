# -*- coding: utf-8 -*-
import logging

from odoo import fields, http, SUPERUSER_ID
from odoo.http import request

_logger = logging.getLogger(__name__)


class Survey(http.Controller):


    @http.route(['/smart_contract/<model("smart.contract"):contract>'],
                type='http', auth='user', website=True)
    def survey_reporting(self, contract, token=None, **post):
        result_template = 'smart_contract.smart_contract_view'
        return request.render(result_template, {'contract': contract})

class ContractReportController(http.Controller):

    @http.route('/report/pdf/smart_contract.smart_contract_pdf_report/<int:contract_id>', type='http', auth='user', website=True)
    def get_contract_pdf_report(self, contract_id, **kwargs):
        # Caută contractul bazat pe ID
        contract = request.env['sale.order'].search([('contract_id', '=', contract_id)], limit=1)
        if not contract:
            return request.not_found()

        # Generează PDF-ul
        pdf = request.env['ir.actions.report']._render_qweb_pdf("smart_contract.smart_contract_pdf_report", contract.contract_id.id)

        # Returnează PDF-ul ca răspuns HTTP
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', f'attachment; filename=contract_{contract_id}.pdf;')
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
