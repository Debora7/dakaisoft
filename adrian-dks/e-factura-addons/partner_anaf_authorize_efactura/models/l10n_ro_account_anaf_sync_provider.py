from odoo import fields, models


class AccountANAFSyncProvider(models.Model):
    _name = "l10n.ro.account.anaf.sync.provider"

    name = fields.Many2one("res.partner", string="Provider Name", required=True)
    url = fields.Char(string="Provider Auth URL", required=True)
