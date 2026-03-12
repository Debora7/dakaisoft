from odoo import api, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def createPo(self):
        PO = self.env['purchase.order']
        for s in self:
            product_lines = s.invoice_line_ids.filtered(lambda x: x.display_type=='product')
            if not all(product_lines.mapped("product_id")):
                raise UserError(_("All lines required to have product in order to create Purchase Order"))
            values = PO.default_get(PO._fields.keys())
            values.update({
                'partner_id': s.partner_id.id,
                'date_approve': s.invoice_date,
                'date_planned': s.invoice_date,
                #'order_line': [(6, 0, ) for line in product_lines]
                })
            pOrder = PO.create(values)
            s.createPOLines(pOrder, product_lines)

    
    def _poValues(self, line):
        line.product_id.standard_price = line.price_unit
        return {
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_qty': line.quantity,
                    'qty_invoiced': line.quantity,
                    'product_uom': line.product_uom_id.id,
                    'invoice_lines': [(6, 0, line.ids)],
                    'taxes_id': [(6, 0, line.tax_ids.ids)],
                    'date_planned': line.move_id.invoice_date,
                    'price_subtotal': line.price_subtotal,
                    'price_unit': line.price_unit,
                    'display_type': False,
                    }
    
    def createPOLines(self, pOrder, invlines):
        POL = self.env['purchase.order.line']
        for line in invlines:
            values = self._poValues(line)
            values.update({'order_id': pOrder.id})
            po_line = POL.create(values)
            #po_line.product_id.standard_price = po_line.price_unit
            
    def _stock_account_get_last_step_stock_moves(self):
        """ Overridden from stock_account.
        Returns the stock moves associated to this invoice."""
        rslt = super(AccountMove, self)._stock_account_get_last_step_stock_moves()
        for invoice in self.filtered(lambda x: x.move_type == 'in_invoice'):
            rslt += invoice.mapped('invoice_line_ids.purchase_line_id.move_ids').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'supplier')
        for invoice in self.filtered(lambda x: x.move_type == 'in_refund'):
            rslt += invoice.mapped('invoice_line_ids.purchase_line_id.move_ids').filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'supplier')
        return rslt