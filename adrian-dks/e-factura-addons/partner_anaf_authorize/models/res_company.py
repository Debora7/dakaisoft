from odoo import _, fields, models
from odoo.exceptions import UserError

class RecCompany(models.Model):
    _inherit = "res.company"

    def _l10n_ro_get_anaf_sync(self, scope=None):
        anaf_sync_scope = super()._l10n_ro_get_anaf_sync(scope=scope)
        return anaf_sync_scope.filtered(lambda x: x.anaf_sync_id.licence_status in ['confirmed_token'])
