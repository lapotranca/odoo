# -*- coding: utf-8 -*-

{
    'name': 'TI AMERICAS Aux Reporting',
    'version': '1.3',
    'summary': 'Modulo auxiliar para reportes.',
    'author': 'TI AMERICAS',
    'website': 'http://www.tiamericas.com/',
    'description': """
        Modulo auxiliar para reportes.
        """,
    'category': 'Accounting/Accounting',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_financial_report_data.xml',
        'views/account_menuitem.xml',
        'views/account_view.xml',   
    ],
    'installable': True,    
    'auto_install': False,
    'application': True,
}
