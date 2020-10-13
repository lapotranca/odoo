# -*- coding: utf-8 -*-

{
    'name': 'TI AMERICAS Odoo Reportes Financieros en PDF',
    'version': '1.1',
    'summary': 'Modulo auxiliar para generar reportes financieros.',
    'category': 'Accounting/Accounting',
    'author': 'TI AMERICAS',
    'license': "AGPL-3",
    'website': 'http://www.tiamericas.com/',
    'description': """
        Modulo auxiliar para generar reportes financieros.
        """,
    'depends': ['account','skit_financial_form'],
    'data': [
        'views/account_menuitem.xml',
        'views/account_report.xml',
        'wizard/account_report_trial_balance_view.xml',        
        'views/report_trialbalance.xml',
        'wizard/account_report_general_ledger_view.xml',
        'views/report_generalledger.xml',
        'wizard/account_financial_report_view.xml',
        'views/report_financial.xml',
        'wizard/account_report_aged_partner_balance_view.xml',        
        'views/report_agedpartnerbalance.xml',
        'wizard/account_report_partner_ledger_view.xml',        
        'views/report_partnerledger.xml',
        'wizard/account_report_print_journal_view.xml',
        'views/report_journal.xml',
        'wizard/account_report_tax_view.xml',
        'views/report_tax.xml',
    ],
    'installable': True,    
    'auto_install': False,
    'application': True,
}
