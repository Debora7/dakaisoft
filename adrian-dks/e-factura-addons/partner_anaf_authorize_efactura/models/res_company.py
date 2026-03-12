import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RecCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_edi_provider_id = fields.Many2one(
        "l10n.ro.account.anaf.sync.provider", string="Provider", required=True
    )
    l10n_ro_edi_licence_status = fields.Selection(
        [
            ("draft", _("Draft")),
            ("waiting_licence", _("Waiting Licence Confirm")),
            ("confirmed_licence", _("Licence Confirmed")),
            ("confirmed_token", _("Token Confirmed")),
            ("blocked", _("Blocked")),
        ],
        string="Status",
        default="draft",
    )
    l10n_ro_edi_error_message = fields.Char(string="Error")
    l10n_ro_edi_provider_licence = fields.Char(string="Provider Licence")

    def get_token_from_anaf_website(self):
        authorization_url = f"{self.l10n_ro_edi_provider_id.url}/partner-licence/anaf-token/{self.l10n_ro_edi_provider_licence}"
        self.l10n_ro_edi_oauth_error = False
        return {
            "type": "ir.actions.act_url",
            "url": authorization_url,
            "target": "self",
        }

    def _l10n_ro_edi_refresh_access_token(self):
        self.ensure_one()
        if self.l10n_ro_edi_provider_id:
            self.env["ir.config_parameter"].sudo().get_param("web.base.url")
            try:
                requests.get(
                    f"{self.l10n_ro_edi_provider_id.url}/partner-licence/anaf-refresh/{self.l10n_ro_edi_provider_licence}",
                    timeout=10,
                )
            except Exception as e:
                raise UserError(_("Got error: %s.") % str(e)) from e
            else:
                pass
        else:
            return super()._l10n_ro_edi_refresh_access_token()
