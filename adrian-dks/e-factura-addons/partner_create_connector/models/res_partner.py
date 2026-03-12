import logging
from odoo import api, fields, models, _


_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    state_code_formatted = fields.Char(string=_("State Code"), compute="_compute_state_data", store=True)
    state_name = fields.Char(string=_("State Name"), compute="_compute_state_data", store=True)

    @api.onchange("vat", "country_id")
    def ro_vat_change(self):
        if not self.country_id:
            self.country_id = self.env.ref("base.ro").id
        res = super(ResPartner, self).ro_vat_change()
        _logger.info(f"{res}")
        if res.get("warning") and self.vat:
            for conn in self.env["partner.create.container"].search([], limit=1).connector_ids.filtered(lambda x: x.is_active):
                content = conn.make_request(partner=self)
                if isinstance(content, list):
                    if any([cnt.get("warning") for cnt in content]):
                        self.ro_vat_change()
                    content = content[0]
                res = content
        return res

    @api.depends("state_id")
    def _compute_state_data(self):
        for rec in self:
            if rec.state_id:
                rec.state_code_formatted = f"{rec.state_id.code}_{rec.state_id.country_id.code}"
                rec.state_name = rec.state_id.name