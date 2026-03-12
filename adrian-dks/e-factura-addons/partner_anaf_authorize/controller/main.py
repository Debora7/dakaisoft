import json

import werkzeug
from odoo import http
from odoo.http import request

import logging
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
        ANAF_Configs = request.env["l10n.ro.account.anaf.sync"].sudo()
        anaf_config = ANAF_Configs.search([("provider_licence", "=", licence)], limit=1)
        write_data = {}
        if not anaf_config:
            website = (
                request.env["ir.config_parameter"].sudo().get_param("web.base.url")
            )
            return {
                "error": True,
                "message": "ANAF Config not found for url: '%s', db: '%s', licence: '%s'."
                % (website, request.env.cr.dbname, kw.get("licence")),
            }
        if kw.get("state"):
            anaf_config.licence_status = (
                kw.get("state") == "open" and "confirmed_licence" or "blocked"
            )
            if anaf_config.licence_status == 'blocked':
                write_data = {
                    "code": "",
                    "access_token": "",
                    "refresh_token": "",
                    "client_token_valability": "",
                }

        _permited = ['code', 'access_token', 'err_message', 'client_token_valability', 'refresh_token']
        write_data.update({key: kw.get(key) for key, __fn in anaf_config._fields.items() if key in kw and key in _permited})

        if kw.get("access_token", None):
            write_data = {
                    "code": kw.get("code"),
                    "access_token": kw.get("access_token"),
                    "refresh_token": kw.get("refresh_token"),
                    "client_token_valability": kw.get("client_token_valability"),
                    "licence_status": "confirmed_token",
                }

        if kw.get("error_msg"):
            write_data = {"err_message": kw.get("error_msg")}

        if write_data:
            anaf_config.write(write_data)

        if kw.get("anaf_env"):
            anaf_config.anaf_scope_ids.write({
                'state': kw.get("anaf_env"),
                })

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
        ANAF_Configs = request.env["l10n.ro.account.anaf.sync"].sudo()
        anaf_config = ANAF_Configs.search(
            [("provider_licence", "=", provider_licence)], limit=1
        )
        return werkzeug.utils.redirect(anaf_config._notify_get_action_link("view"))
