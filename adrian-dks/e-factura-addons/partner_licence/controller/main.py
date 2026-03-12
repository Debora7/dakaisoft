import json

from odoo import http
from odoo.http import request


class LicenceController(http.Controller):
    @http.route(
        "/partner-licence/register",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def customerEnrole(self, **kw):
        json_data = json.loads(request.httprequest.data)
        kw.update(json_data)
        res = request.env["res.partner.licence"].enrole_customer(**kw)
        return res
