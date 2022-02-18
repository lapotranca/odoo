# Copyright 2016 Vauxoo Oscar Alcala <oscar@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
{
    "name": "Download ZIP file with invoices XML UUID",
    "summary": """
        Adds the option to download XML UUID from invoices
        using ZIP file.
    """,
    "version": "13.0.1.0.1",
    "author": "Vauxoo",
    "category": "Localization/Mexico",
    "website": "http://www.vauxoo.com/",
    "license": "LGPL-3",
    "depends": [
        'l10n_mx_edi_uuid',
    ],
    "demo": [
    ],
    "data": [
        'data/ir_actions_server_data.xml',
        'data/mail_message_subtype_data.xml',
    ],
    "installable": True,
    "auto_install": False,
}
