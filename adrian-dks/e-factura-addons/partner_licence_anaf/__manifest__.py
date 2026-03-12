{
    "name": "Partner Licence Anaf",
    "description": "",
    "version": "19.0.0.0",
    "website": "https://dakai.ro",
    "author": "Dakai SOFT SRL",
    "maintainers": ["adrian-dks"],
    "license": "OPL-1",
    "installable": True,
    "data": [
        "security/ir.model.access.csv",
        "views/oauth_anaf.xml",
        "views/customer_licence.xml",
        "data/data.xml",
    ],
    "category": "Licence for Anaf",
    "depends": ["partner_licence", "l10n_ro_account_anaf_sync"],
    "external_dependencies": {"python": ["PyJWT"]},
}
