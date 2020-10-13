# -*- coding: utf-8 -*-

{
    'name': 'TI AMERICAS Reporte Financiero Localizacion Mexicana l10n_mx_reports',
    'version': '1.0',
    'summary': 'Reporte Financiero Localizacion Mexicana',
    'category': 'Accounting/Accounting',
    'author': 'TI AMERICAS',
    'description': """
        Modulo auxiliar para generar reportes financieros.
        """,
    'website': 'http://www.tiamericas.com/',
    'depends': ['account_accountant', 'account_reports','skit_financial_report', 'l10n_mx_reports'],
    'data': [
        'data/data.xml',
        'views/assets.xml',
        'views/account_report_view.xml',
        'views/search_template_view.xml',

    ],
    'qweb': [
    ],
    'demo': [
    ],
    'css': [
    ],
    'installable': True,    
    'auto_install': False,
    'application': True,    
}
