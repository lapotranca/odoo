# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "UUID Search Invoices",
    "summary": """
        Adds the option to search by the uuid of the attachment
        of the invoice by default when searching for the name
    """,
    "version": "13.0.1.0.3",
    "author": "Vauxoo",
    "category": "Localization/Mexico",
    "website": "http://www.vauxoo.com/",
    "license": "LGPL-3",
    "depends": [
        'l10n_mx_edi',
    ],
    "demo": [
    ],
    "data": [
        'views/account_invoice_views.xml',
        'views/ir_attachment_views.xml',
        'views/account_payment_views.xml',
    ],
    "installable": True,
    "auto_install": False,
    "post_init_hook": "post_init_hook",
}
