from odoo import models, fields


class EdiDocument(models.Model):
    _inherit = "account.edi.document"

    l10n_ro_reload_einvoice = fields.Boolean()

    def l10n_ro_set_bloching_level_error(self):
        self.ensure_one()
        self.l10n_ro_reload_einvoice = True
        self.move_id.l10n_ro_edi_transaction = None
        self.move_id.l10n_ro_edi_download = None
