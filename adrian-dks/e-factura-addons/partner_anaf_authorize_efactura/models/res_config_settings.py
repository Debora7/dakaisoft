import json
import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ro_edi_provider_id = fields.Many2one(
        related="company_id.l10n_ro_edi_provider_id", readonly=False
    )
    l10n_ro_edi_licence_status = fields.Selection(
        related="company_id.l10n_ro_edi_licence_status", readonly=False
    )
    l10n_ro_edi_provider_licence = fields.Char(
        related="company_id.l10n_ro_edi_provider_licence", readonly=False
    )

    def button_l10n_ro_edi_generate_token(self):
        """Redirects to controllers/main.py ~ `authorize` method"""
        self.ensure_one()
        if self.company_id.l10n_ro_edi_provider_id:
            return self.company_id.get_token_from_anaf_website()
        return super().button_l10n_ro_edi_generate_token()

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
                f"{self.l10n_ro_edi_provider_id.url}/partner-licence/register",
                json=params,
                timeout=10,
            )
        except Exception as e:
            raise UserError(_("Got error: %s.") % str(e)) from e
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
            self.l10n_ro_edi_provider_licence = res["response_data"].get("licence")
            self.l10n_ro_edi_licence_status = (
                res["response_data"].get("state") == "closed"
                and "waiting_licence"
                or "confirmed_licence"
            )
        else:
            self.l10n_ro_edi_licence_status = "blocked"
        return True
