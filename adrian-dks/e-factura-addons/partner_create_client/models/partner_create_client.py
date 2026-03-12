from odoo import api, fields, models, _


class PartnerCreateClient(models.Model):
    _name = "partner.create.client"

    name = fields.Char(string=_("Name"))
    endpoint = fields.Char(string=_("Endpoint"))
    licence = fields.Char(string=_("Licence"))