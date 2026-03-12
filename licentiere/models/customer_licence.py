from odoo import api, fields, models


class PartnerLicence(models.Model):
    _inherit = "res.partner.licence"

    expiration_date = fields.Date(string="Expiration Date", help="The date when the license expires.")
    hw_key = fields.Char(string="Hardware Key", help="The hardware key associated with the license.")
    scope = fields.Selection(selection_add=[
        ("server", "Server Fiscal")
    ])

    @api.depends("partner_id", "scope", "licence")
    def _compute_RecordName(self):
        super()._compute_RecordName()
        for s in self:
            if s.hw_key:
                s.name = f"[{s.scope or s.partner_id.vat}] {s.partner_id.name} - {s.hw_key}"

    def cron_check_licences(self):
        licences = self.env['res.partner.licence'].search([('state', '=', 'open')])
        for licence in licences:
            if licence.expiration_date and licence.hw_key and licence.expiration_date < fields.Date.today():
                licence.state = 'closed'

    def cron_notify_licence_expiry(self):
        today = fields.Date.today()
        soon = today + timedelta(days=3)
        expiring_licences = self.search([('expiration_date', '<', soon)])
        users = self.env['res.users'].search([('company_id', '=', self.env.company.id), ('email', '!=', False)])
        email_list = ','.join(users.mapped('email'))
        template = self.env.ref('licentiere.email_template_licence_expiry')
        for licence in expiring_licences:
            template.with_context(email_to=email_list).send_mail(licence.id, force_send=True)