# -*- coding: utf-8 -*-
{
  'name':'Etransport-addon',
  'description': "",
  'version':'16.0.0.1',
  'author':'Dakai SOFT',
  'website': 'https://dakai.ro',
  'author': 'Dakai SOFT SRL',
  'maintainers': ["adrian-dks"],
  'license': 'OPL-1',
  'installable': True,
  'data': [
    #'security/ir.model.access.csv',
    'views/e_trans_picking.xml',
    'views/e_transport_template.xml',
    'views/stock_picking_batch.xml',
    ],
  'category': 'Stock',
  'depends': ['l10n_ro_etransport'],
}
