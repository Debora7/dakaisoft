from odoo import _, fields, models
from odoo.exceptions import UserError

class RecCompany(models.Model):
    _inherit = "res.company"

    provider_id = fields.Many2one(
        "l10n.ro.account.anaf.sync.provider", string="Provider", required=True
    )
    licence_status = fields.Selection(
        [
            ("draft", _("Draft")),
            ("waiting_licence", _("Waiting Licence Confirm")),
            ("confirmed_licence", _("Licence Confirmed")),
            ("confirmed_token", _("Token Confirmed")),
            ("blocked", _("Blocked")),
        ],
        string=_("Status"),
        default="draft",
    )
    err_message = fields.Char(string="Error")
    provider_licence = fields.Char(string="Provider Licence")
    code = fields.Char(help="Received from ANAF with this you can take access token and refresh_token")
    def _l10n_ro_get_anaf_sync(self, scope=None):
        anaf_sync_scope = super()._l10n_ro_get_anaf_sync(scope=scope)
        return anaf_sync_scope.filtered(lambda x: x.anaf_sync_id.licence_status in ['confirmed_token'])

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
