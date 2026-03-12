# -*- coding: utf-8 -*-
{
  'name':'Dakai inv2po',
  'description': "",
  'version':'16.0.0.1',
  'author':'Dakai SOFT',
  'website': 'https://dakai.ro',
  'author': 'Dakai SOFT SRL',
  'maintainers': ["adrian-dks"],
  'license': 'OPL-1',
  'installable': True,
  'data': [
    'views/account_invoice.xml',
    #'security/ir.model.access.csv',
    ],
  'category': 'Accounting',
  'depends': ['l10n_ro_account_edi_ubl','purchase_enterprise'],
}
