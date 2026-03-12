{
  'name':'Partner Create Connector',
  'description': "Partner Create Connector with other API's",
  'version':'1.0',
  'author':'Dakai SOFT',
  'data': [
    "security/ir.model.access.csv",
    "views/partner_create_connector.xml"
  ],
  'category': 'CRM',
  'depends': ['base', 'contacts', "l10n_ro_partner_create_by_vat", "l10n_ro_vat_on_payment", "partner_licence"],
}
