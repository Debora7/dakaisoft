from odoo import api, fields, models, _


class PartnerLicence(models.Model):
    _inherit = "res.partner.licence"

    scope = fields.Selection(
        selection_add=[
            ("partner_create", _("Partner Create")),
        ]
    )
