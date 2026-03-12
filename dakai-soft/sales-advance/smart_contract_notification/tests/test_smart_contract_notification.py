from odoo.tests import TransactionCase

class TestSmartContractNotification(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.smart_contract = cls.env['smart.contract'].create({
            'company_id': 1,
            'currency_id': 1,
            'type': 'custommer',
            'document_type': 'notificare',
        })

    def test_get_regulation_required_compute(self):
        self.assertEqual(self.smart_contract._get_regulation_required_compute(), True)

    def test_compute_show_regulation(self):
        self.assertEqual(self.smart_contract._compute_show_regulation(), True)