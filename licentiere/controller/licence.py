from odoo import http
from odoo.http import request
from odoo import tools, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError
import logging
import json

_logger = logging.getLogger(__name__)

class LicenseController(http.Controller):

    @http.route('/checkLicence', type='json', auth='public', methods=['POST'], csrf=False)
    def check_licence_provider(self, **kwargs):
        kwargs = request.get_json_data()
        res = {
            'error': False,
            'message': _("Firma a fost gasita in baza de date"),
        }
        domain = [('is_company', '=', True)]
        if kwargs.get('firm_cui'):
            domain.append(('vat', '=', kwargs.get('firm_cui')))
        partner = request.env['res.partner'].sudo().search(domain, limit=1)
        license_ids = request.env['res.partner.licence'].sudo().search([('hw_key', '=', kwargs.get('device_uuid'))])
        if license_ids:
            for l in license_ids:
                res.update({
                    'LicenceKey': l.licence,
                    'ExpirationDate': l.expiration_date,
                    'IsValid': True if l.state == 'open' else False,
                })
                if not l.partner_id and partner:
                    l.write({
                        'partner_id': partner.id,
                        'vat': partner.vat,
                    })
        elif len(license_ids) == 0:
            res_partner_licence = request.env['res.partner.licence']
            new_licence = res_partner_licence.sudo().create({
                'licence': res_partner_licence._generateLicenceString(),
                'partner_id': partner.id if partner and kwargs.get("firm_cui") else False,
                'hw_key': kwargs.get('device_uuid'),
                'expiration_date': datetime(2025, 12, 31),
                'username': kwargs.get('firm_name', ''),
                'scope': 'server',
                'state': 'open',
            })
            if not partner:
                new_licence.write({
                    'vat': kwargs.get('firm_cui', ''),
                })
            res.update({
                'LicenceKey': new_licence.licence,
                'ExpirationDate': new_licence.expiration_date,
                'IsValid': True,
            })
        if res.get('IsValid') == False:
            res.update({
                'error': True,
                'message': _("Licenta nu este valida sau a expirat"),
            })
        return res
