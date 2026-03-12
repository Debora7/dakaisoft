import logging
import secrets
from datetime import datetime, timedelta
import jwt
import requests
from odoo import _, http
from odoo.http import request
from werkzeug.utils import redirect
import jwt

_logger = logging.getLogger(__name__)


class AnafLicenceController(http.Controller):
    def redirect_anaf(self, config, **kw):
        uid = request.uid
        user = request.env["res.users"].browse(uid)
        client_id = config.client_id
        url = user.get_base_url()
        odoo_oauth_url = f"{url}/partner-licence/anaf_oauth/{config.id}"
        redirect_url = f"""{
            config.anaf_oauth_url}/authorize?response_type=code&client_id={
            client_id}&redirect_uri={
            odoo_oauth_url}&token_content_type=jwt"""
        _logger.info(f"__Redirect URL__redirect_anaf {redirect_url}")
        anaf_request_from_redirect = request.redirect(
            redirect_url, code=302, local=False
        )
        return anaf_request_from_redirect

    def redirectFromError(self, Licence, error_msg):
        json_dump = {"error_msg": error_msg}
        data_dump = Licence and Licence.json_data or {}
        data_dump.update(json_dump)
        Licence.json_data = data_dump
        url_to_redirect = Licence.prepare_redirect("Error")
        return redirect(url_to_redirect)

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
        Licence._freez_transactions()

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

    @http.route(
        "/partner-licence/anaf-revoke/<string:licence_code>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def customer_revoke_token(self, licence_code, **kw):
        Licence, check_perm = self._checkPermissions(licence_code, **kw)
        if check_perm.error:
            return self.redirectFromError(Licence, check_perm.values.get("message"))
        Licence._revokeToken()
        url_to_redirect = Licence.prepare_redirect("Success")
        return redirect(url_to_redirect)

    @http.route(
        "/partner-licence/anaf-refresh/<string:licence_code>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def customer_refresh_token(self, licence_code, **kw):
        Licence, check_perm = self._checkPermissions(licence_code, **kw)
        if check_perm.error:
            return self.redirectFromError(Licence, check_perm.values.get("message"))
        Licence._refreshToken()
        url_to_redirect = Licence.prepare_redirect("Success")
        return redirect(url_to_redirect)

    @http.route(
        ["/partner-licence/anaf_oauth/<int:config_id>"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        csrf=False,
    )
    def get_anaf_oauth_code(self, config_id, **kw):
        "Returns a text with the result of anaf request from redirect"
        _logger.info(f"__Date From anaf__get_anaf_oauth_code {config_id, kw}")
        uid = request.uid
        user = request.env["res.users"].browse(uid)
        now = datetime.now()
        ANAF_Configs = request.env["partner.licence.anaf_oauth"].sudo()
        config = ANAF_Configs.browse(config_id)
        licence = config._activeLicence()

        message = ""

        if not config:
            message = _("No ANAF config was found for this company.")

        if message:
            values = {"message": message}
            return request.render("l10n_ro_account_anaf_sync.redirect_anaf", values)

        code = kw.get("code")
        if code:
            headers = {
                "content-type": "application/x-www-form-urlencoded",
                "accept": "application/json",
                "user-agent": "PostmanRuntime/7.29.2",
            }
            url = user.get_base_url()
            redirect_uri = f"{url}/partner-licence/anaf_oauth/{config_id}"
            data = {
                "grant_type": "authorization_code",
                "client_id": f"{config.client_id}",
                "client_secret": f"{config.client_secret}",
                "code": f"{code}",
                "access_key": f"{code}",
                "redirect_uri": f"{redirect_uri}",
                "token_content_type": "jwt"
            }
            _logger.info(f"__Data__get_anaf_oauth_code {data, headers}")

            response = requests.post(
                config.anaf_oauth_url + "/token",
                data=data,
                headers=headers,
                timeout=1.5,
            )

            response_json = response.json()
            acces_token = {}
            if response_json.get("access_token", None):
                acces_token = jwt.decode(
                    response_json.get("access_token"),
                    algorithms=["RS512"],
                    options={"verify_signature": False},
                )
            message = _("The response was finished.\nResponse was: %s") % response_json
            json_dump = {
                "client_id": f"{config.client_id}",
                "client_secret": f"{config.client_secret}",
                "code": code,
                "client_token_valability": datetime.fromtimestamp(
                        acces_token.get("exp", 0)
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                "last_request_datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "access_token": response_json.get("access_token", ""),
                "refresh_token": response_json.get("refresh_token", ""),
                "refresh_token_valability": (now + timedelta(days=1095)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "refresh_token_used": 0,  # 64 max
            }
            licence = config.saveData2Licence(json_dump)
        else:
            message = _("No code was found in the response.\nResponse was: %s") % kw
            licence._release_transactions()
            return self.redirectFromError(licence, message)
        licence._release_transactions()
        url_to_redirect = licence.prepare_redirect(message)
        return redirect(url_to_redirect)
