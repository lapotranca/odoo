# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2019. All rights reserved.

{
    'name': 'Special Purchase Approval for Certain Products',
    'version': '13.0.0.2',
    'category': 'Operations/Purchase',
    'summary': 'Special Purchase Approval',
    'sequence': 1,
    'author': 'Technaureus Info Solutions Pvt. Ltd.',
    'description': 'Special Purchase Approval To Confirm The Purchase Order',
    'website': 'http://www.technaureus.com',
    'license': 'Other proprietary',
    'price': 9.99,
    'currency': 'EUR',
    'depends': [
        'purchase',
    ],
    'data': [
        'views/product_template_view.xml',
    ],
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
