import json
import logging

import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AccountANAFAuthorize(http.Controller):
    @http.route(
        "/partner-licence/update-partner-licence",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def update_partner_licence(self, **kw):
        licence = request.httprequest.args.get("licence")
        json_data = json.loads(request.httprequest.data)
        kw.update(json_data)
        Companies = request.env["res.company"].sudo()
        company = Companies.search(
            [("l10n_ro_edi_provider_licence", "=", licence)], limit=1
        )
        write_data = {}
        if not company:
            website = (
                request.env["ir.config_parameter"].sudo().get_param("web.base.url")
            )
            return {
                "error": True,
                "message": "Company not found for url: '{}', db: '{}', licence: '{}'.".format(
                    website, request.env.cr.dbname, kw.get("licence")
                ),
            }
        if kw.get("state"):
            company.l10n_ro_edi_licence_status = (
                kw.get("state") == "open" and "confirmed_licence" or "blocked"
            )
            if company.l10n_ro_edi_licence_status == "blocked":
                write_data = {
                    "l10n_ro_edi_access_token": "",
                    "l10n_ro_edi_refresh_token": "",
                    "l10n_ro_edi_access_expiry_date": "",
                    "l10n_ro_edi_refresh_expiry_date": "",
                }

        if kw.get("access_token", None):
            company._l10n_ro_edi_process_token_response(kw)
            company.write(
                {
                    "l10n_ro_edi_licence_status": "confirmed_token",
                }
            )

        if kw.get("error_msg"):
            write_data = {"l10n_ro_edi_oauth_error": kw.get("error_msg")}

        if kw.get("anaf_env"):
            company.write(
                {
                    "l10n_ro_edi_test_env": kw.get("anaf_env") == "production"
                    and False
                    or True,
                }
            )

        _logger.debug(f"write_data_______________{write_data}")
        return {"error": False, "message": "Success"}

    @http.route(
        "/partner-licence/callback-anaf-oauth/<string:provider_licence>",
        type="http",
        auth="public",
        website=True,
        csrf=False,
    )
    def callback_anaf_oauth(self, provider_licence, **kw):
        Company = request.env["res.company"].sudo()
        company = Company.search(
            [("l10n_ro_edi_provider_licence", "=", provider_licence)], limit=1
        )
        return werkzeug.utils.redirect(company._notify_get_action_link("view"))
