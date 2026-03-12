from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends('bank_partner_id', 'currency_id')
    def _compute_partner_bank_id(self):
        super(AccountMove, self)._compute_partner_bank_id()
        for move in self:
            bank = move.partner_bank_id
            bank_ids = move.bank_partner_id.bank_ids.filtered(
                lambda bank: ((not bank.company_id or  # check if bank belong to company
                              bank.company_id == move.company_id) and
                              bank.l10n_ro_print_report and  # is printed on report
                              (bank.currency_id or move.company_id.currency_id  # same currency
                               ) == move.currency_id and
                              bank in (move.journal_id.permited_bank_ids or bank)
                              )
                )
            if bank_ids:
                bank = bank_ids[0]
            move.partner_bank_id = bank

