# -*- coding: utf-8 -*-
{
  'name': 'Invoice in diffrent currency than sale',
  'description': "Conver amount on diffrent currency",
  'version': '19.0.0.0.0',
  'website': 'https://dakai.ro',
  'author': 'Dakai SOFT SRL',
  'maintainers': ["adrian-dks"],
  'license': 'OPL-1',
  'installable': True,
  'data': [
    'wizard/sale_invoice_advance.xml',
    ],
  'category': 'Accounting',
  'depends': ['account','sale'],
}