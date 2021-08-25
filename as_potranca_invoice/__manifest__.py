# -*- coding: utf-8 -*-
{
    'name' : "Ahorasoft POTRANCA customizaciones",
    'version' : "1.1.1",
    'author'  : "Ahorasoft",
    'description': """
Customizaciones para POTRANCA
===========================

Custom module for POTRANCA
    """,
    'category' : "Sale",
    'depends' : ["base","stock","hr_expense","as_financial_report","account","report_qweb_element_page_visibility"],
    'website': 'http://www.ahorasoft.com',
    'data' : [
        # 'security/ir.model.access.csv',
        'view/as_res_users.xml',
        'view/report/as_invoice_report_document.xml',
             ],
    'demo' : [],
    'installable': True,
    'auto_install': False
}
