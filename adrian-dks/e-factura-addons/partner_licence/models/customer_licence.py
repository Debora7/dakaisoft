import random
import string
from datetime import timedelta
from urllib.parse import urlparse

import requests
from odoo import api, fields, models

_MAX_TIME = 300  # seconds


class Bunch(object):
    def __init__(self, adict):
        self.__dict__.update(adict)

class partnerLicence(models.Model):
    _name = "res.partner.licence"
    _description = "Partner Licence"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(compute="_compute_RecordName", store=True)
    scope = fields.Selection([("none", "No scope")], "Licence Scope", default="none")
    partner_id = fields.Many2one("res.partner", help="Customer Company")
    vat = fields.Char(
        compute="_compute_customer_vat",
        inverse="_set_customer_vat",
        help="Customer VAT",
        store=True,
    )
    json_data = fields.Json()
    username = fields.Char()
    licence = fields.Char()
    database = fields.Char()
    url = fields.Char()  # base_url
    state = fields.Selection(
        [
            ("open", "Open"),
            ("closed", "Closed"),
        ],
        default="closed",
    )
    to_update = fields.Boolean(default=False)
    to_update_datetime = fields.Datetime()
    anaf_env = fields.Selection([("test", "Test"), ("production", "Production")])

    @api.depends("partner_id", "scope", "licence")
    def _compute_RecordName(self):
        for s in self:
            s.name = f"[{s.scope or s.partner_id.vat}] {s.partner_id.name}"

    def _set_customer_vat(self):
        for s in self:
            partner = self.env["res.partner"].search(
                [
                    ("vat", "=", s.vat),
                    ("is_company", "=", True),
                    ("parent_id", "=", False),
                ],
                limit=1,
            )
            s.partner_id = partner and partner.id or None

    def _compute_customer_vat(self):
        for s in self:
            s.vat = s.partner_id.vat

    def _getBaseUrl(self):
        pars_url1 = urlparse(self.url)
        pars_url = urlparse(f"{pars_url1.scheme}://{pars_url1.netloc}")
        return pars_url.geturl()

    def _getCustomerUrl(self):
        base_url = self._getBaseUrl()
        url = f"{base_url}/partner-licence/update-partner-licence"
        return url

    def _send_data_to_customer(self):
        for s in self:
            if s.state == "close":
                continue
            customer_url = s._getCustomerUrl()
            url = f"{customer_url}?db={s.database}&licence={s.licence}"
            res = requests.post(url, json=s.json_data)
            response = ""
            try:
                info = res.json()
            except:
                response = res.text
            else:
                response = info.get("message", "Succes: No message set")
            s.message_post(body=response)

    def write(self, value):
        res = super(partnerLicence, self).write(value)
        if value.get("json_data"):
            self._send_data_to_customer()
        return res

    def _generateLicenceString(self):
        def getRandomStr():
            letters = "".join(
                [string.ascii_uppercase, "".join([str(i) for i in range(0, 9)])]
            )
            ch = "".join(random.choice(letters) for i in range(16))
            return "-".join([ch[x * 4 : x * 4 + 4] for x in range(4)])

        def hashGen(new=None):
            if not new:
                new = getRandomStr()
            self._cr.execute(
                "SELECT count(*) as s from res_partner_licence where licence = %s",
                (new,),
            )
            res = self._cr.fetchone()
            if res[0] > 0:
                return hashGen(getRandomStr())
            return new

        return hashGen()

    @api.model
    def _getLicences(self, **kw):
        if kw.get("licence", None):
            return self.sudo().search([("licence", "=", kw.get("licence"))])
        elif kw.get("url", None) and kw.get("vat", None):
            return self.sudo().search(
                [("url", "=", kw.get("url")), ("vat", "=", kw.get("vat"))]
            )
        return self

    @api.model
    def getLicences(self, **kw):
        return self._getLicences(**kw)

    @api.model
    def getActiveLicences(self, **kw):
        return self._getLicences(**kw).filtered(lambda x: x.state == "open")

    def _prepare_licence_values(self, values):
        return values

    @api.model
    def enrole_customer(self, **kw):
        msg = {
            "data": kw,
            "error": True,
            "date": fields.Datetime.now(),
            "message": "Request not procesed yet or generic error",
            "response_data": {},
        }
        if not all(
            [
                kw.get("username"),
                kw.get("database"),
                kw.get("url"),
                kw.get("vat"),
            ]
        ):
            msg[
                "message"
            ] = "Required data is not present: {username, database, url, vat}"

        # Check permision
        Licences = self.getLicences(**kw)
        if len(Licences) == 1:
            Licence = Licences
            msg["message"] = f"Licence already exists {Licence.licence}"
            msg["response_data"].update(
                {
                    "licence": Licence.licence,
                    "vat": Licence.vat,
                    "state": Licence.state,
                }
            )
        elif len(Licences) > 1:
            Licences.write({"state": "closed"})
            msg["message"] = f"Licence error, contact your parthner"
            msg["response_data"].update(
                {
                    "licence": None,
                    "state": "closed",
                }
            )
        elif not Licences:
            create_value = self._prepare_licence_values(
                {
                    "licence": self._generateLicenceString(),
                    "username": kw.get("username"),
                    "database": kw.get("database"),
                    "url": kw.get("url"),
                    "vat": kw.get("vat"),
                }
            )
            Licence = self.sudo().create(create_value)
            msg["error"] = False
            msg["message"] = f"New licence is created {Licence.licence}"
            msg["response_data"].update(
                {
                    "licence": Licence.licence,
                    "vat": Licence.vat,
                    "state": Licence.state,
                }
            )
        return msg


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