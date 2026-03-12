from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends('product_id', 'product_uom_id')
    def _compute_price_unit(self):
        price_unit_mapped = {line: line.price_unit for line in self if line.move_id.l10n_ro_edi_download}
        super(AccountMoveLine, self)._compute_price_unit()
        for line, price in price_unit_mapped.items():
            line.price_unit = price

    @api.depends('product_id')
    def _compute_name(self):
        name_mapped = {line: line.name for line in self if line.move_id.l10n_ro_edi_download}
        super(AccountMoveLine, self)._compute_name()
        for line, name in name_mapped.items():
            line.name = name

