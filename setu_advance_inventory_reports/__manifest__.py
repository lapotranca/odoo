# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Advance Inventory Reports',
    'version' : '13.0',
    'price' : 299,
    'currency'  :'EUR',
    'category': 'stock',
    'summary': """	
        Advance Inventory Reports / Inventory Analysis Reports
        - Inventory Turnover Analysis Report / Inventory Turnover Ratio
            Inventory turnover is a ratio showing how many times a company has sold and replaced inventory during a given period.
    
        - Inventory FSN Analysis Report / non moving report / stock movement
            This classification is based on the consumption pattern of the products i.e. movement analysis forms the basis. 
            Here the items are classified into fast moving, slow moving and non-moving on the basis of frequency of transaction. 
    
        - Inventory XYZ Analysis Report
            XYZ Analysis is always done for the current Stock in Inventory and aims at classifying the items into three classes on the basis of their Inventory values.
            
        - Inventory FSN with XYZ Analysis Report / FSN-XYZ Analysis / FSN XYZ Analysis
            FSN Classification analysis along with XYZ Classification
            
        - Inventory Age Report / stock ageing / Inventory ageing / stock age
            Inventory age report is useful to determine how oldest your inventories are.
            It gives you detailed analysis products wise about oldest inventories at company level.
        
        - Inventory Age Breakdown Report 
            Inventory age breakdown report is useful to determine how oldest your inventories are.
            It gives you detailed breakdown analysis products wise about oldest inventories at company level.
            
        - Inventory Overtsock Report / Excess Inventory Report  
            Excess Inventory Report is used to capture all products which are having overstock than needed.
        
        - Stock Movement Report / Stock Rotation Report
            Stock movement report is used to capture all the transactions of products between specific time frame.   
   
        - Inventory Out Of Stock Report / inventory coverage report / outofstock report
            Inventory OutOfStock Report is used to capture all products which are having demand but stock shortage as well.

	- Advanced Inventory Reports / All in one inventory reports / all in one reports
	Reports used to analyse inventories by different inventory management techniques.
		""",
    'website' : 'https://www.setuconsulting.com' ,
    'support' : 'support@setuconsulting.com',
    'description' : """
        Advance Inventory Reports / Inventory Analysis Reports
        ===================================================================
        - Inventory Turnover Analysis Report
            Inventory turnover is a ratio showing how many times a company has sold and replaced inventory during a given period.
    
        - Inventory FSN Analysis Report
            This classification is based on the consumption pattern of the products i.e. movement analysis forms the basis. 
            Here the items are classified into fast moving, slow moving and non-moving on the basis of frequency of transaction. 
    
        - Inventory XYZ Analysis Report
            XYZ Analysis is always done for the current Stock in Inventory and aims at classifying the items into three classes on the basis of their Inventory values.
            
        - Inventory FSN with XYZ Analysis Report
            FSN Classification analysis along with XYZ Classification
            
        - Inventory Age Report
            Inventory age report is useful to determine how oldest your inventories are.
            It gives you detailed analysis products wise about oldest inventories at company level.
        
        - Inventory Age Breakdown Report
            Inventory age breakdown report is useful to determine how oldest your inventories are.
            It gives you detailed breakdown analysis products wise about oldest inventories at company level.
            
        - Inventory Overtsock Report / Excess Inventory Report  
            Excess Inventory Report is used to capture all products which are having overstock than needed.
        
        - Stock Movement Report / Stock Rotation Report
            Stock movement report is used to capture all the transactions of products between specific time frame.   
   
        - Inventory Out Of Stock Report
            Inventory OutOfStock Report is used to capture all products which are having demand but stock shortage as well.
    """,
    'author' : 'Setu Consulting',
    'license' : 'OPL-1',
    'sequence': 25,
    'depends' : ['sale_stock'],
    'images': ['static/description/banner.gif'],
    'data' : [
        'views/setu_stock_movement_report.xml',
        'views/setu_inventory_turnover_analysis_report.xml',
        'views/setu_inventory_fsn_analysis_report.xml',
        'views/setu_inventory_xyz_analysis_report.xml',
        'views/setu_inventory_fsn_xyz_analysis_report.xml',
        'views/setu_inventory_overstock_report.xml',
        'views/setu_inventory_outofstock_report.xml',
        'views/setu_inventory_age_report.xml',
        'views/setu_inventory_age_breakdown_report.xml',
    ],
    'application': True,
    'pre_init_hook': 'pre_init',
    'live_test_url' : 'http://95.111.225.133:8889/web/login',
}
