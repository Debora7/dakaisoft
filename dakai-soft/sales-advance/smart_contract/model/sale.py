import base64
from odoo import fields, models, _


class Sale(models.Model):
    _inherit = "sale.order"
    
    contract_id = fields.Many2one("smart.contract", _("Contract"))

    def action_create_contract(self):
        values = {'partner_id': self.partner_id.id,'document_type':'contract'}
        self.contract_id = self.env['smart.contract'].create(values)
        self.action_add_attachment()

    def action_open_smart_contract(self):
        self.ensure_one()
        action = self.env.ref('smart_contract.action_smart_contract').read()[0]
        action['domain'] = [('id', '=', self.contract_id.id)]
        return action


    def action_add_attachment(self):
        pdf = self.env['ir.actions.report']._render_qweb_pdf("smart_contract.smart_contract_pdf_report", self.contract_id.id)
        b64_pdf = base64.b64encode(pdf[0])
        name = self.contract_id.name
        return self.env['ir.attachment'].create({
            'name': f'{name}.pdf',
            'type': 'binary',
            'datas': b64_pdf,
            'store_fname': name,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/x-pdf'
        })

    def action_send_contract_via_message_compose(self):
        self.ensure_one()

        pdf = self.env['ir.actions.report']._render_qweb_pdf("smart_contract.smart_contract_pdf_report", self.contract_id.id)
        pdf_attachment = self.env['ir.attachment'].create({
            'name': f'Contract_{self.name}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf[0]),
            'res_model': 'sale.order',
            'res_id': self.id,
            'mimetype': 'application/pdf'
        })

        template_id = self.env.ref('smart_contract.template_contract_email').id
        compose_form_id = self.env.ref(
            'mail.email_compose_message_wizard_form').id

        ctx = {
            'default_model': 'sale.order',
            'default_res_ids': self.ids,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'force_email': True,
            'default_attachment_ids': [(6, 0, [pdf_attachment.id])],
        }

        return {
            'name': 'Send Contract',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }