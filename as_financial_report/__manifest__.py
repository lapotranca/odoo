# -*- coding: utf-8 -*-

{
    'name': 'TI AMERICAS Pivote Financiero',
    'version': '1.2.5',
    'author': 'TI AMERICAS',
    'website': 'http://www.tiamericas.com/',
    'summary': 'Pivote Financiero',
    'description': """
            Pivote Financiero
    """,
    'category': 'Accounting/Accounting',
    'depends': ['account','hr','purchase','sale','analytic','hr_expense','sale_enterprise','account_reports','account_dynamic_reports','skit_financial_form'],
    'data': [
            'views/report_wizard.xml',
            'views/account_menus.xml',
            'views/profit_loss_report_view.xml',
            'views/account_move.xml',
            'views/employee_views.xml',
            'views/purchase_order.xml',
            'views/sale_order.xml',
            'views/stock_expense_hr.xml',
            'views/balance_sheet_report_view.xml',
            'views/as_product_template.xml',
            'views/as_stock_move_line.xml',
            'views/as_config_settings.xml',
            'wizard/as_general_ledger.xml',
            'report/as_report_sale_pivot.xml',
            'security/ir.model.access.csv',
            'security/as_group_view.xml',
            ],
    'auto_install': False,
    'application': True,
    'installable': True,
}
