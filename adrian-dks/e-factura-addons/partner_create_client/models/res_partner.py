import json
import logging
import requests
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def get_partner_data(self):
        config = self.env["partner.create.client"].sudo().search([], limit=1)
        url = f"{config.endpoint}/get-partner/{config.licence}/{self.vat}"
        res = requests.get(url)
        _logger.info(f"{res.content}")
        if res.status_code > 400:
            raise ValidationError(f"{res.content}")
        vals = json.loads(res.content)
        self.update(vals)