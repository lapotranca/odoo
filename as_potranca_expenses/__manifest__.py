# -*- coding: utf-8 -*-
{
    'name' : "Ahorasoft POTRANCA customizaciones",
    'version' : "1.0.6",
    'author'  : "Ahorasoft",
    'description': """
Customizaciones para POTRANCA
===========================

Custom module for POTRANCA
    """,
    'category' : "Sale",
    'depends' : ["base","stock","hr_expense","as_financial_report"],
    'website': 'http://www.ahorasoft.com',
    'data' : [
        # 'security/ir.model.access.csv',
        'wizard/as_invoice_expense_wiz.xml',
        'view/as_hr_expense.xml',
        'view/as_product_template.xml',
             ],
    'demo' : [],
    'installable': True,
    'auto_install': False
}
