# -*- coding: utf-8 -*-

# Copyright 2017-2018 Devendra kavthekar <https://twitter.com/kdevendr>
# Website: <https://dek-odoo.github.io>

{
    "name": "POS Lot Selection",
    "summary": "Select lot when selling product",
    "category": "Point of Sale",
    "version": "13.0.1.1",

    "description": """

POS Lot Selection
    1.A pop up with list of lots to pick products from in POS
    2.Validations to prevent invalid user inputs
    3.User-friendly flow to manage lots and locations
    4.Easily installable and compatible with your existing POS module

""",

    "application": False,
    "sequence": 7,

    "author": "Devendra kavthekar",
    "support": "dkatodoo@gmail.com",
    "website": "https://dek-odoo.github.io",
    "license": "OPL-1",
    "price": 70.00,
    "currency": "EUR",
    "images": ["static/description/banner.gif"],

    "depends": ["point_of_sale"],
    "data": [
        "views/assets.xml",
        "security/ir.model.access.csv",
    ],

    "qweb": [
        "static/src/xml/point_of_sale.xml",
    ],
    # "installable": True,
    "auto_install": False,
}
