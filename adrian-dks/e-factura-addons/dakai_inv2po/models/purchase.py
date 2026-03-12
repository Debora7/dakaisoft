from odoo import api, fields, models

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    
    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        res = super(PurchaseOrderLine, self)._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        return res
    
    def _create_stock_moves(self, picking):
        move = super(PurchaseOrderLine, self)._create_stock_moves(picking)
        return move