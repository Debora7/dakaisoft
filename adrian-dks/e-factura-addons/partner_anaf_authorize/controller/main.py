import json
import secrets
import requests
import jwt
from werkzeug.urls import url_encode
import werkzeug
from odoo import http, _
from odoo.http import request
from datetime import datetime, timedelta

import logging

_logger = logging.getLogger(__name__)


class AccountANAFAuthorize(http.Controller):

    def _checkPermissions(self, licence_code, **kw):
        httprequest = http.request.httprequest
        referer = httprequest.environ.get("HTTP_REFERER")

        POL = request.env["res.partner.licence"].sudo()
        kw.update(
            {
                "licence": licence_code,
                "referer": referer,
            }
        )
        kw.update(
            {
                "licence_entry": POL.getActiveLicences(**kw),
            }
        )
        kw.get("licence_entry")
        check_perm = POL._checkPermission(**kw)
        return kw.get("licence_entry"), check_perm

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
        ANAF_Configs = request.env["res.company"].sudo()
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
                    "l10n_ro_edi_client_id": "",
                    "l10n_ro_edi_client_secret": "",
                    "l10n_ro_edi_access_token": "",
                    "l10n_ro_edi_refresh_token": "",
                    "l10n_ro_edi_access_expiry_date": "",
                    "l10n_ro_edi_refresh_expiry_date": "",
                }

        _permited = ['code', 'l10n_ro_edi_access_token', 'err_message', 'l10n_ro_edi_access_expiry_date', 'l10n_ro_edi_refresh_token', 'l10n_ro_edi_refresh_expiry_date', 'l10n_ro_edi_client_id', 'l10n_ro_edi_client_secret']
        write_data.update(
            {key: kw.get(key) for key, __fn in anaf_config._fields.items() if key in kw and key in _permited})

        if kw.get("access_token", None):
            _logger.error(f"ANAF {kw}")
            write_data = {
                "code": kw.get("code"),
                "l10n_ro_edi_client_id": kw.get("client_id"),
                "l10n_ro_edi_client_secret": kw.get("client_secret"),
                "l10n_ro_edi_access_token": kw.get("access_token"),
                "l10n_ro_edi_refresh_token": kw.get("refresh_token"),
                "l10n_ro_edi_access_expiry_date": kw.get("client_token_valability"),
                "l10n_ro_edi_refresh_expiry_date": kw.get("refresh_token_valability"),
                "licence_status": "confirmed_token",
            }

        if kw.get("error_msg"):
            write_data = {"err_message": kw.get("error_msg")}

        if write_data:
            anaf_config.write(write_data)

        # if kw.get("anaf_env"):
            # _logger.error(f"anaf {kw.get('anaf_env'), anaf_config.read()}")
            # anaf_config.anaf_scope_ids.write({
            #     'state': kw.get("anaf_env"),
            #     })

        _logger.error(f"write_data_______________{write_data, kw}")
        return {"error": False, "message": "Success"}

    @http.route(
        "/partner-licence/callback-anaf-oauth/<string:provider_licence>",
        type="http",
        auth="public",
        website=True,
        csrf=False,
    )
    def callback_anaf_oauth(self, provider_licence, **kw):
        ANAF_Configs = request.env["res.company"].sudo()
        anaf_config = ANAF_Configs.search(
            [("provider_licence", "=", provider_licence)], limit=1
        )

        return werkzeug.utils.redirect(anaf_config._notify_get_action_link("view"))

    @http.route(
        "/partner-licence/anaf-token/<string:licence_code>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def customerGenToken(self, licence_code, **kw):
        Licence, check_perm = self._checkPermissions(licence_code, **kw)
        if check_perm.error:
            return self.redirectFromError(Licence, check_perm.values.get("message"))
        # Licence._freez_transactions()

        config = Licence.oauth_id
        if not config.client_id or not config.client_secret:
            error = (
                f"Error, on ANAF company config {config.name} you does not have a "
                f"Oauth client_id or client_secret for anaf.ro!"
            )
            return self.redirectFromError(Licence, error)
        now = datetime.now()
        if (
                config.last_request_datetime
                and config.last_request_datetime + timedelta(seconds=60) > now
        ):
            error = _("You can make only one request per minute")
            return self.redirectFromError(Licence, error)

        secret = secrets.token_urlsafe(16)

        config.write(
            {
                "response_secret": secret,
                "last_request_datetime": now,
            }
        )
        return self.redirect_anaf(config, **kw)
