from datetime import datetime, timedelta
import jwt
import requests
from odoo import _, fields, models

_MAX_TIME = 300  # seconds


class Bunch(object):
    def __init__(self, adict):
        self.__dict__.update(adict)


class partnerLicence(models.Model):
    _inherit = "res.partner.licence"

    oauth_id = fields.Many2one("partner.licence.anaf_oauth")
    # scope = fields.Selection(
    #     selection_add=[
    #         ("e-factura", "RO E-Factura"),
    #         ("e-transport", "RO E-Transport"),
    #     ]
    # )
    to_update = fields.Boolean(default=False)
    to_update_datetime = fields.Datetime()
    anaf_env = fields.Selection([("test", "Test"), ("production", "Production")])

    def _refreshToken(self):
        self._freez_transactions()
        config = self.oauth_id
        json_dump = self.json_data
        licence_data = Bunch(json_dump)
        param = f"""client_id={config.client_id}&client_secret={config.client_secret}&refresh_token={licence_data.refresh_token}&grant_type=refresh_token"""
        url = f"{config.anaf_oauth_url}/token"
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "accept": "application/json",
            "user-agent": "PostmanRuntime/7.29.2",
        }
        response = requests.post(
            url,
            data=param,
            timeout=80,
            headers=headers,
        )
        response_json = response.json()
        if response.status_code == 200:
            message = _("Refresh token response: %s") % response.json()
        else:
            message = _("Refresh token response: %s") % response.reason
        now = datetime.now()
        models._logger.debug(f"Mesaj anaf {response.status_code}, {response.text}")
        if response.status_code == 200:
            acces_token = jwt.decode(
                response_json.get("access_token"),
                algorithms=["RS512"],
                options={"verify_signature": False},
            )
            json_dump.update(
                {
                    "access_token": response_json.get("access_token", ""),
                    "refresh_token": response_json.get("refresh_token", ""),
                    "last_request_datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "client_token_valability": datetime.fromtimestamp(
                                acces_token.get("exp", 0)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                    "refresh_token_used": licence_data.refresh_token_used + 1,  # 64 max
                }
            )
            models._logger.debug(f"DUMP {json_dump}")
            config.saveData2Licence(json_dump)
        self._release_transactions()
        return True

    def _revokeToken(self):
        self._freez_transactions()
        config = self.oauth_id
        json_dump = {
            "code": "",
            "access_token": "",
            "refresh_token": "",
            "last_request_datetime": False,
            "client_token_valability": False,
            "refresh_token_valability": False,
        }
        config.saveData2Licence(json_dump)
        self._release_transactions()
        return True

    def _send_data_to_customer(self):
        super(partnerLicence, self)._send_data_to_customer()
        self.write({"to_update": False, "to_update_datetime": None})

    def _checkPermission(self, *args, **kwargs):
        # Close orphan requests above
        self.search(
            [
                (
                    "to_update_datetime",
                    "<=",
                    (fields.Datetime.now() - timedelta(seconds=_MAX_TIME)),
                ),
                ("to_update", "=", True),
            ]
        ).write(
            {
                "to_update": False,
                "to_update_datetime": None,
            }
        )
        # Direct in SQL NOW() e `with timezone`, ceea ce face un decalaj de fus orar, convertirea la timestamp, mareste la Ex: 2ore + _MAX_TIME
        # Pentru un trafic mai mare este nevoie ca anularea request orfane, sa fie procesate direct in SQL.
        # self._cr.execute("UPDATE res_partner_licence SET to_update_datetime=NULL, to_update=FALSE where to_update=TRUE and to_update_datetime <= (CURRENT_TIMESTAMP(0) - interval '%s seconds')::timestamp;", (_MAX_TIME,))
        check = self.search([("to_update", "=", True)])

        res = Bunch({"error": False, "values": {}})

        messages = {}

        if len(check) != 0:
            diff_time = fields.Datetime.now() - check.to_update_datetime
            df_sec = _MAX_TIME - (diff_time.days * 12 * 60 * 60 + diff_time.seconds)
            tformat = divmod(df_sec, 60)
            df_min = ":".join([str(tformat[0]), str(round(tformat[1], 0))])
            messages = {"message": f"Busy...Waiting time {df_min} minutes..."}
            res.error = True

        if not kwargs.get("licence_entry", None):
            messages = {"message": f"Restricted! No licence"}
            res.error = True

        if kwargs.get("referer", None) and kwargs.get("licence_entry", None):
            licence = kwargs.get("licence_entry")
            if licence.url not in kwargs.get("referer"):
                messages = {"message": f"Wrong request origin"}
                res.error = True

        res.values = messages
        return res

    def setAnafEnvProduction(self):
        self.write({"anaf_env": "production"})

    def setAnafEnvTest(self):
        self.write({"anaf_env": "test"})

    def write(self, vals):
        if vals.get("state"):
            vals["json_data"] = {
                "state": vals.get("state")
                }
        elif vals.get("anaf_env", None):
            anaf_env = vals.get("anaf_env")
            for s in self:
                params = s.json_data
                params.update(
                    {
                        "anaf_env": anaf_env,
                    }
                )
                super(partnerLicence, s).write({"json_data": params})
                models._logger.debug(f"==================>{s.json_data, params, vals}")
        return super(partnerLicence, self).write(vals)

    def _freez_transactions(self):
        self.write({"to_update": True, "to_update_datetime": fields.Datetime.now()})

    def _release_transactions(self):
        self.write(
            {
                "to_update": False,
                "to_update_datetime": None,
            }
        )

    def _get_oauth_id(self, scope=None):
        return (
            self.sudo()
            .env["partner.licence.anaf_oauth"]
            .search([
                #("scope", "=", scope)
                ], limit=1)
            .id
        )

    def _prepare_licence_values(self, values):
        values.update({"oauth_id": self._get_oauth_id(values.get("scope"))})
        return values

    def prepare_redirect(self, message):
        if len(self) == 0:
            return "/"
        base_url = self._getBaseUrl()
        url = f"{base_url}/partner-licence/callback-anaf-oauth/{self.licence}?message={message}"
        return url

    def cronRefreshTokens(self):
        refresh = self
        revoke = self
        for licence in self.search([("state", "=", "open")]):
            data = licence.json_data
            if (
                datetime.strptime(
                    data.get("client_token_valability", "2024-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S"
                ).date()
                <= datetime.now().date()
                and data.get("refresh_token_used", 0) == 64
            ):
                revoke |= licence
            elif (
                datetime.strptime(
                    data.get("refresh_token_valability", "2024-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S"
                ).date()
                <= datetime.now().date()
            ):
                revoke |= licence
            elif (
                datetime.strptime(
                    data.get("client_token_valability", "2024-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S"
                ).date()
                <= datetime.now().date()
            ):
                refresh |= licence

        for licence_to_revoke in revoke:
            licence_to_revoke._revokeToken()

        for licence_to_refresh in refresh:
            licence_to_refresh._refreshToken()
