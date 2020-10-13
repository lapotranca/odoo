# -*- coding: utf-8 -*-
{
    'name': "TI AMERICAS Webservice IDI",

    'summary': """
        Webservice IDI
        """,

    'description': """
       Webservice IDI
    """,

    'author': 'TI AMERICAS',
    'Maintainer':"Carlos Paz",
    'website': 'http://www.tiamericas.com/',

    'category': 'Integration',
    'version': '13.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'mail',
        'base',
    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'wizard/sale_whatsapp_wizard.xml',
        # 'views/as_config_settings.xml',
        'views/as_users.xml',
    ],
    # 'qweb': [
    #     'static/src/xml/mobile_widget.xml',
    # ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
}
