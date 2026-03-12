from odoo import fields, models


class oAuthAnaf(models.Model):
    _name = "partner.licence.anaf_oauth"

    name = fields.Char(default="New")
    anaf_oauth_url = fields.Char(default="https://logincert.anaf.ro/anaf-oauth2/v1")
    anaf_callback_url = fields.Char(
        compute="_compute_anaf_callback_url",
        help="This is the address to set in anaf_portal_url "
        "(and will work if is https & accessible form internet)",
    )
    client_id = fields.Char(
        help="From ANAF site the Oauth id - view the readme",
        tracking=1,
    )
    client_secret = fields.Char(
        help="From ANAF site the Oauth id - view the readme",
        tracking=1,
    )
    # scope = fields.Selection(
    #     [
    #         ("e-factura", "RO E-Factura"),
    #         ("e-transport", "RO E-Transport"),
    #     ],
    #     string="Scope",
    # )
    last_request_datetime = fields.Datetime(
        help="Time when was last time pressed the Get Token From Anaf Website."
        " It waits for ANAF request for maximum 1 minute",
    )
    response_secret = fields.Char(
        help="A generated secret to know that the response is ok"
    )
    licence_ids = fields.One2many("res.partner.licence", "oauth_id")
    #
    # test_url_anaf = fields.Char(required=True)
    # production_url_anaf = fields.Char(required=True)

    def _compute_anaf_callback_url(self):
        for s in self:
            url = s.get_base_url()
            s.anaf_callback_url = f"{url}/partner-licence/anaf_oauth/{s.id}"

    def _activeLicence(self):
        return self.licence_ids.filtered(lambda x: x.to_update)

    def saveData2Licence(self, data):
        update_licence = self._activeLicence()
        data_dump = {
            "licence": update_licence.licence,
            "state": update_licence.state,
        }  # update_licence.json_data
        data_dump.update(data)
        update_licence.write(
            {
                "json_data": data_dump,
            }
        )
        return update_licence
