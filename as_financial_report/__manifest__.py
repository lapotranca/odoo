# -*- coding: utf-8 -*-

{
    'name': 'TI AMERICAS Pivote Financiero',
    'version': '1.0.9',
    'author': 'TI AMERICAS',
    'website': 'http://www.tiamericas.com/',
    'summary': 'Pivote Financiero',
    'description': """
            Pivote Financiero
    """,
    'category': 'Accounting/Accounting',
    'depends': ['account','skit_financial_form','hr','purchase','sale','analytic','hr_expense','sale_enterprise'],
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
            'report/as_report_sale_pivot.xml',
            'security/ir.model.access.csv',
            ],
    'auto_install': False,
    'application': True,
    'installable': True,
}
