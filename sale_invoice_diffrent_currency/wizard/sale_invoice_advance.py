from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    second_currency_id = fields.Many2one("res.currency", string="Invoice Currency", default=lambda x: x.env.company.currency_id.id)

    def create_invoices(self):
        self_currency = self
        if self.second_currency_id:
            self_currency = self.with_context(second_currency_id=self.second_currency_id)
        return super(SaleAdvancePaymentInv, self_currency).create_invoices()

    def _prepare_invoice_values(self, order, so_line):
        self_currency = self
        if self.second_currency_id:
            self_currency = self.with_context(second_currency_id=self.second_currency_id)
        return super(SaleAdvancePaymentInv, self_currency)._prepare_invoice_values()

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        if self._context.get('second_currency_id'):
            new_currency = self._context.get('second_currency_id')
            res['currency_id'] = new_currency.id
        return res

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        if self._context.get('second_currency_id'):
            new_currency = self._context.get('second_currency_id')
            res['price_unit'] = self.currency_id.compute(res['price_unit'], new_currency)
        return res