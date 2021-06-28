# -*- coding: utf-8 -*-
{
    'name' : "Ahorasoft THIEMED customizaciones",
    'version' : "1.0.4",
    'author'  : "Ahorasoft",
    'description': """
Customizaciones para POTRANCA
===========================

Custom module for POTRANCA
    """,
    'category' : "Sale",
    'depends' : ["base","stock","hr_expense"],
    'website': 'http://www.ahorasoft.com',
    'data' : [
        # 'security/ir.model.access.csv',
        # 'security/sale_stock_security.xml',
        'wizard/as_invoice_expense_wiz.xml',
        'view/as_hr_expense.xml',
        'view/as_product_template.xml',
        # 'view/as_modelo_item.xml',
        # 'view/as_product_template.xml',
        # 'view/as_produt_superr.xml',
        # 'view/sale_order_inherit_view.xml',
        # 'view/as_sales_config_setting.xml',
             ],
    'demo' : [],
    'installable': True,
    'auto_install': False
}
