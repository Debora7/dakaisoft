from odoo.tests import TransactionCase
from odoo.fields import Datetime

class TestSale(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'autopost_bills': 'always',
            'name': 'Partner'
        })
        
        cls.sale_order = cls.env['sale.order'].create({
            'company_id': 1,
            'date_order': Datetime.now(),
            'name': 'Sale order for test',
            'partner_id': cls.partner.id,
            'partner_invoice_id': cls.partner.id, 
            'partner_shipping_id': cls.partner.id,
        })
        
    def test_action_create_contract(self):
        self.sale_order.action_create_contract()
        
        self.assertTrue(self.sale_order.contract_id)
        
    def test_action_open_smart_contract(self):
        self.sale_order.action_create_contract()
        action = self.sale_order.action_open_smart_contract()
        
        self.assertEqual(action['domain'], [('id', '=', self.sale_order.contract_id.id)])
        
    def test_action_add_attachment(self):
        return True
    
    def test_action_send_contract_via_message_compose(self):
        return True