# -*- coding: utf-8 -*-
{
  'name':'Dakai specific bank acc invoice',
  'description': "",
  'version':'19.0.0.0.0',
  'author':'Dakai SOFT',
  'website': 'https://dakai.ro',
  'author': 'Dakai SOFT SRL',
  'maintainers': ["adrian-dks"],
  'license': 'OPL-1',
  'installable': True,
  'data': [
    #'security/ir.model.access.csv',
    "views/account_journal.xml"
    ],
  'category': 'Accounting',
  'depends': ['account','l10n_ro_config'],
}
