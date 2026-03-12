from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    l10n_ro_remorca1 = fields.Char(string="Remorca 1")
    l10n_ro_remorca2 = fields.Char(string="Remorca 2")
    l10n_ro_doc_type = fields.Selection([
        ("10", "CMR"),
        ("20", "Invoice"),
        ("30", "Picking Document"),
        ("9999", "Others")
        ], string="Delivery Document Type", default="30")
    l10n_ro_doc_type_nr = fields.Char(string="Transport doc. No.")
    l10n_ro_doc_type_date = fields.Date(string="Transport doc. date")

    @api.onchange('l10n_ro_doc_type')
    def _onchange_doc_type(self):
        if self.l10n_ro_doc_type == '30':
            self.l10n_ro_doc_type_nr = self.name
            self.l10n_ro_doc_type_date = self.date
