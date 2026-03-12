from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    company_bank_ids = fields.Many2many("res.partner.bank", compute="_compute_company_bank_ids")
    permited_bank_ids = fields.Many2many("res.partner.bank", string="Permited bank")

    @api.depends('company_id')
    def _compute_company_bank_ids(self):
        for s in self:
            s.company_bank_ids = [(6, 0,
                                   s.company_id.partner_id.bank_ids.filtered(
                                       lambda x: x.l10n_ro_print_report
                                       ).ids)]
