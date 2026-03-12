import logging
import markupsafe
from odoo import api, fields, models, _
from lxml import etree
from odoo.addons.l10n_ro_etransport.models import stock_picking
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
STATE_CODES = stock_picking.STATE_CODES


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    l10n_ro_carrier_id = fields.Many2one("delivery.carrier", string="Carrier", check_company=True)
    l10n_ro_e_transport_partner_id = fields.Many2one("res.partner", string="Partner", compute="_compute_same_partner")
    l10n_ro_e_transport_uit = fields.Char(string="UIT", copy=False)
    l10n_ro_e_transport_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("ok", "Ok"),
            ("nok", "Not OK"),
            ("in_processing", "In processing"),
        ],
        default="draft",
    )
    l10n_ro_e_transport_download = fields.Char(
        "ID Download ANAF ",
        copy=False,
    )
    l10n_ro_e_transport_message = fields.Text("ANAF Message")

    l10n_ro_e_transport_operation_type_id = fields.Many2one(
        "l10n.ro.e.transport.operation",
        string="Operation type",
        default=lambda self: self.env.ref(
            "l10n_ro_etransport.operation_30", raise_if_not_found=False
        ),
    )

    l10n_ro_e_transport_scope_id = fields.Many2one(
        "l10n.ro.e.transport.scope", string="Scope"
    )

    l10n_ro_e_transport_customs_id = fields.Many2one(
        "l10n.ro.e.transport.customs", string="Border crossing point"
    )

    l10n_ro_vehicle = fields.Char(string="Vehicle")
    l10n_ro_remorca1 = fields.Char(string="Trailer 1")
    l10n_ro_remorca2 = fields.Char(string="Trailer 2")
    l10n_ro_doc_type = fields.Selection([
        ("10", "CMR"),
        ("20", "Invoice"),
        ("30", "Picking Document"),
        ("9999", "Others")
        ], string="Delivery Document Type", default="30")
    l10n_ro_doc_type_nr = fields.Char(string="Transport doc. No.")
    l10n_ro_doc_type_date = fields.Date(string="Transport doc. date")

    @api.onchange('l10n_ro_doc_type')
    def _onchange_doc_type(self):
        if self.l10n_ro_doc_type == '30':
            self.l10n_ro_doc_type_nr = self.name
            self.l10n_ro_doc_type_date = self.scheduled_date

    def _compute_same_partner(self):
        for s in self:
            partner = s.picking_ids.mapped("partner_id")
            s.l10n_ro_e_transport_partner_id = len(partner)==1 and partner.id or None

    def _export_e_transport(self):

        def get_country_code(country_code):
            if country_code == "GR":
                country_code = "EL"
            return country_code

        def get_instastat_code(product):
            intrastat_code = "00000000"  # 08031010
            if "hs_code" in product._fields:
                intrastat_code = product.hs_code or intrastat_code
            if "intrastat_code_id" in product._fields:
                intrastat_code = product.intrastat_code_id.code or intrastat_code

            return intrastat_code

        self.ensure_one()

        if not self.l10n_ro_e_transport_partner_id:
            message = _("Validation Error: No Partner is set\nPosible reason: picking with diffrent destinations")
            _logger.error(message)
            raise UserError(message)

        # Create file content.
        xml_declaration = markupsafe.Markup("<?xml version='1.0' encoding='UTF-8'?>\n")

        render_values = {
            "doc": self,
            "company": self.company_id,
            "STATE_CODES": STATE_CODES,
            "get_country_code": get_country_code,
            "get_instastat_code": get_instastat_code,
        }
        View = self.env["ir.ui.view"].sudo()
        xml_content = View._render_template(
            "etransport_addons.e_transport_batch", render_values
        )
        xml_name = "%s_e_transport.xml" % (self.name.replace("/", "_"))
        xml_content = xml_declaration + xml_content

        _logger.info(xml_content)
        xml_doc = etree.fromstring(xml_content.encode())
        schema_file_path = get_module_resource(
            "l10n_ro_etransport", "static/schemas", "eTransport.xsd"
        )
        xml_schema = etree.XMLSchema(etree.parse(open(schema_file_path)))

        is_valid = xml_schema.validate(xml_doc)

        if not is_valid:
            message = _("Validation Error: %s") % xml_schema.error_log.last_error
            _logger.error(message)
            raise UserError(message)

        domain = [
            ("name", "=", xml_name),
            ("res_model", "=", "stock.picking"),
            ("res_id", "=", self.id),
        ]
        attachments = self.env["ir.attachment"].search(domain)
        attachments.unlink()
        self.picking_ids.write({
                        'carrier_id': self.l10n_ro_carrier_id.id,
                        'l10n_ro_e_transport_uit': self.l10n_ro_e_transport_uit,
                        'l10n_ro_e_transport_status': self.l10n_ro_e_transport_status,
                        'l10n_ro_e_transport_download': self.l10n_ro_e_transport_download,
                        'l10n_ro_e_transport_message': self.l10n_ro_e_transport_message,
                        'l10n_ro_e_transport_operation_type_id': self.l10n_ro_e_transport_operation_type_id.id,
                        'l10n_ro_e_transport_scope_id': self.l10n_ro_e_transport_scope_id.id,
                        'l10n_ro_e_transport_customs_id': self.l10n_ro_e_transport_customs_id.id,
                        'l10n_ro_vehicle': self.l10n_ro_vehicle,
                        'l10n_ro_remorca1': self.l10n_ro_remorca1,
                        'l10n_ro_remorca2': self.l10n_ro_remorca2,
                        'l10n_ro_doc_type': self.l10n_ro_doc_type,
                        'l10n_ro_doc_type_nr': self.l10n_ro_doc_type_nr,
                        'l10n_ro_doc_type_date': self.l10n_ro_doc_type_date,
                    })
        return self.env["ir.attachment"].create(
            {
                "name": xml_name,
                "raw": xml_content,
                "res_model": "stock.picking",
                "res_id": self.id,
                "mimetype": "application/xml",
            }
        )

    def export_e_transport_button(self):
        if self.l10n_ro_e_transport_status in ["draft", "nok"]:
            attachment = self._export_e_transport()
            self._export_e_transport_data(attachment.raw)
        elif self.l10n_ro_e_transport_status in ["sent", "in_processing"]:
            anaf_config = self.company_id._l10n_ro_get_anaf_sync(scope="e-transport")
            params = {}
            func = f"/stareMesaj/{self.l10n_ro_e_transport_download}"
            content, status_code = anaf_config._l10n_ro_etransport_call(
                func, params, method="GET"
            )
            if status_code != 200:
                raise UserError(
                    _("Error %(status_code)s:%(content)s")
                    % {"status_code": status_code, "content": content}
                )
            _logger.info(content)
            stare = content.get("stare")

            if stare == "ok":
                self.write({"l10n_ro_e_transport_status": stare})

            if stare == "nok":
                errors = content.get("Errors", [])
                error_message = "".join(
                    [error.get("errorMessage", "") for error in errors]
                )
                message = _("The document is not ok. Errors: %s") % error_message
                self.write(
                    {
                        "l10n_ro_e_transport_status": "nok",
                        "l10n_ro_e_transport_message": message,
                    }
                )
            if stare == "in prelucrare":
                message = _("The document was in processing at %s.") % content.get(
                    "dateResponse"
                )
                self.write(
                    {
                        "l10n_ro_e_transport_status": "in_processing",
                        "l10n_ro_e_transport_message": message,
                    }
                )

    @api.model
    def _export_e_transport_data(self, data):

        anaf_config = self.company_id._l10n_ro_get_anaf_sync(scope="e-transport")
        params = {}
        standard = "ETRANSP"
        cif = self.company_id.partner_id.vat.replace("RO", "")

        func = f"/upload/{standard}/{cif}/2"
        content, status_code = anaf_config._l10n_ro_etransport_call(func, params, data)
        if status_code != 200:
            raise UserError(
                _("Error %(status_code)s:%(content)s")
                % {"status_code": status_code, "content": content}
            )

        errors = content.get("Errors", [])
        error_message = "".join([error.get("errorMessage", "") for error in errors])
        if error_message:
            raise UserError(error_message)

        message = _("The document was uploaded successfully, check the status.")
        self.write(
            {
                "l10n_ro_e_transport_uit": content.get("UIT"),
                "l10n_ro_e_transport_status": "sent",
                "l10n_ro_e_transport_download": content.get("index_incarcare"),
                "l10n_ro_e_transport_message": message,
            }
        )

        _logger.info(content)
        _logger.info(status_code)
