import json
import werkzeug
from odoo import http
from odoo.http import request

import logging
import requests
from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class PartnerLicenceAuthorize(http.Controller):
    def get_licence(self):
        website = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        if not self.company_id.vat:
            raise UserError(_("Company VAT is mandatory!"))
        params = {
            "username": self.env.user.login,
            "database": self.env.cr.dbname,
            "url": website,
            "vat": self.company_id.vat,
        }
        try:
            r = requests.post(
                "%s/partner-licence/register" % self.provider_id.url, json=params
            )
        except Exception as e:
            raise UserError(_("Got error: %s.") % str(e))
        if r.status_code != requests.codes.ok:
            raise UserError(
                _("Got an error %s when trying to request licence.") % r.status_code
            )
        res = json.loads(r.text, strict=False)["result"]
        if res.get("error") and not res["response_data"].get("licence"):
            raise UserError(
                _("Got an error when trying to request licence:  %s") % r.get("message")
            )
        if res["response_data"].get("licence"):
            self.provider_licence = res["response_data"].get("licence")
            self.licence_status = (
                res["response_data"].get("state") == "closed"
                and "waiting_licence"
                or "confirmed_licence"
            )
        else:
            self.licence_status = "blocked"
        return True


    @http.route(
        "/partner-licence/get_interval",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def get_interval(self, **kwargs):
        POL = request.env["res.partner.licence"]
        POL.getActiveLicences(**kwargs)
        if not POL:
            return {'interval': 60}
