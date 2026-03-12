import json
import logging

import requests
from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    provider_id = fields.Many2one(related='company_id.provider_id', string="Provider", readonly=False)
    licence_status = fields.Selection(related='company_id.licence_status', string=_("Status"), readonly=False)
    err_message = fields.Char(related='company_id.err_message', string="Error", readonly=False)
    provider_licence = fields.Char(related='company_id.provider_licence', string="Provider Licence", readonly=False)
    code = fields.Char(related='company_id.code', string="Code", readonly=False)

    def get_anaf_licence(self):
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

    def get_token_from_anaf_website(self):
        authorization_url = (
            f"{self.provider_id.url}/partner-licence/anaf-token/{self.provider_licence}"
        )
        self.err_message = False
        return {
            "type": "ir.actions.act_url",
            "url": authorization_url,
            "target": "self",
        }

    def revoke_access_token(self):
        self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        try:
            requests.get(
                f"{self.provider_id.url}/partner-licence/anaf-revoke/{self.provider_licence}"
            )
        except Exception as e:
            raise UserError(_("Got error: %s.") % str(e))
        else:
            self.licence_status = "confirmed_licence"

    def refresh_access_token(self):
        self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        try:
            requests.get(
                f"{self.provider_id.url}/partner-licence/anaf-refresh/{self.provider_licence}"
            )
        except Exception as e:
            raise UserError(_("Got error: %s.") % str(e))
        else:
            pass

    def button_l10n_ro_edi_generate_token_auth(self):
        self.ensure_one()
        if self.company_id.provider_id:
            return self.company_id.get_token_from_anaf_website()
        return super().button_l10n_ro_edi_generate_token()


class AccountANAFSyncProvider(models.Model):
    _name = "l10n.ro.account.anaf.sync.provider"

    name = fields.Many2one("res.partner", string="Provider Name", required=True)
    url = fields.Char(string="Provider Auth URL", required=True)
