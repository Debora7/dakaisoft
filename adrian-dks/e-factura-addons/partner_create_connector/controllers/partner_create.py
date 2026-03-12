import json
from odoo.http import Controller, request, route

DEFAULT_FIELDS = ["name", "street", "street2", "city", "zip", "state_code_formatted", "state_name",
                  "country_code", "contact_address", "vat", "company_registry", "nrc", "phone",
                  "mobile", "email", "l10n_ro_caen_code", "l10n_ro_vat_subjected", "l10n_ro_vat_on_payment"]


class PartnerCreate(Controller):
    @staticmethod
    def _verify_fields(fields):
        partner_fields = request.env["ir.model.fields"].sudo().search([("model", "=", "res.partner")])
        fields = [k for k in fields if k in partner_fields.mapped("name")]
        yield fields

    @route("/get-partner/<string:licence>/<string:vat>", type="http", auth="public", methods=["GET"])
    def search_partner(self, licence, vat, **kwargs) -> str:
        licence = request.env["res.partner.licence"].sudo().search([("licence", "=", licence)], limit=1)
        if licence:
            partner = request.env["res.partner"].sudo().search([("vat", "like", vat)], limit=1)
            if not partner:
                partner = partner.create({"name": "default", "vat": vat})
                partner.ro_vat_change()
            fields_list = next(self._verify_fields(kwargs.get("fields", "").split(",")))
            fields = list(filter(None, fields_list)) or DEFAULT_FIELDS
            clear_partner = partner.read(fields)[0]
            clear_partner.pop("id")
            return json.dumps(clear_partner)
        return json.dumps({"error": "Invalid Licence!"})
