# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': "Car Repair Management Odoo",
    'currency': 'EUR',
    'license': 'Other proprietary',
    'summary': """This app allow you to repair industry of Cars. Car Repair Request, Car Diagnosis, Car Repair Job Order Management""",
    'price': 99.0,
    'author': "Probuse Consulting Service Pvt. Ltd.",
    'website': "http://www.probuse.com",
    'support': 'contact@probuse.com',
    'images': ['static/description/img1.jpeg'],
    'live_test_url':'https://youtu.be/Iuzun3k6z5I',
    'version': '2.0.8',
    'category' : 'Project',
    'depends': [
                'project',
                'hr_timesheet',
                'portal',
                'sales_team',
                'stock',
#                'document', odoo13
                'sale_management',
                'website',
                ],
    'data':[
        'security/car_repair_security.xml',
        'security/ir.model.access.csv',
#        'views/assets.xml', odoo13 not used
        'report/car_repair_request.xml',
        'datas/car_repair_support_sequence.xml',
        'datas/mail_template_ticket.xml',
        'views/car_repair_support_view.xml',
        'views/car_repair_support_template.xml',
        'views/hr_timesheet_sheet_view.xml',
        'views/support_team_view.xml',
        'views/my_ticket.xml',
        'views/ticket_attachment.xml',
        'views/successfull.xml',
        'views/task.xml',
        'views/feedback.xml',
        'views/thankyou.xml',
        'report/car_repair_analysis.xml',
        'views/product_template_view.xml',
        'views/repair_types_view.xml',
        'views/product_consume_part_view.xml',
        'views/nature_of_service_view.xml',
        'views/repair_estimation_lines_view.xml',
        'report/report_car_repair_lable.xml',
        'views/menus.xml',
        'views/sale_order_view.xml',
    ],
    'description': """
Car Repair Request and Management
repair management
car_repair_industry
Car Repair Management Odoo/OpenERP
all type of car repair
machine repair
repair order
repair app
repair management
odoo repair
Car Repair Management
car repair website
website car repair request by customer
Create car repair order
Add car service details.
Create car diagnosis.
car diagnosis
car_repair_industry
Car Repair industry
car repair
fleet repair
car repair
bike repair
fleet management
odoo repair
repair odoo
car maintenance
maintenance odoo
repair maintenance
maintenance management
fleet maintenance
odoo maintenance
maintenance request
repair request
repair online
repair customer car
customer car repair
maintenance handling
Car Repair Services
star
washers
bearings
set
screws
Car Diagnosis
snap
Car Repair
Car Repair/Car Repair / Service
Car Repair/Car Repair / Service/Car Diagnosys
Car Repair/Car Repair / Service/Car Repair / Services
Car Repair/Car Repair / Service/Car WorkOrders
Car Repair Request, Car Diagnosis, Car Repair Job Order Management

Car Repair/Cars
Car Repair/Cars/Car Parts
Car Repair/Cars/Cars
Car Repair/Configuration
Car Repair/Configuration/Car Repair Teams
Car Repair/Configuration/Service Types
Car Repair/Configuration/Services
Car Repair/Reports 

Car Repair View
rings
Car Label Report
car
Car & Service Details
Car and Service Details
Car Receipt Report
screws
Car Repair Order
sheaves
chain
sprockets
gears
shafts
wheels
collars
fabrications
plates
covers
ratchets
pinions
hubs
springs
drums
overhaul
airframe components
assembly
engine parts
landing gear components
air conditioning	16600000
air conditioner	13600000
ac air conditioning	9140000
furnace	5000000
air conditioners	3350000
hvac	1830000
air condition	1500000
trane	1220000
air con	1220000
hvac air conditioning	1000000
heat pump	823000
heating air	823000
heating & air	823000
heating and air	823000
air conditioning units	823000
air conditioning unit	823000
air conditioner unit	673000
air conditioner units	673000
heating & cooling	673000
cooling and heating	673000
heating and cooling	673000
air conditioning cooling	673000
heat and air	550000
air conditioning and heating	550000
heating and air conditioning	550000
heating air conditioning	550000
heating & air conditioning	550000
air conditioning heating	550000
portable air conditioner	450000
air conditioner portable	450000
central air	368000
mustufa rangwala
portable air conditioning	368000
air conditioning portable	368000
portable air conditioners	368000
air conditioners portable	368000
air conditioning system	368000
air conditioning repair	301000
repair air conditioning	301000
air conditioner price	301000
window air conditioner	301000
air conditioner repair	246000
portable air conditioning units	246000
repair air conditioner	246000
air conditioning systems	246000
air conditioner system	246000
portable air conditioning unit	246000
ac compressor	246000
split air conditioner	246000
duct cleaning	201000
air conditioning price	201000
ac unit	201000
air conditioner prices	201000
window air conditioning	201000
window air conditioners	201000
air conditioning service	201000
service air conditioning	201000
cost air conditioner	201000
air conditioner cost	201000
ac repair	165000
cost of air conditioning	165000
air conditioning cost	165000
air conditioning compressor	165000
air conditioning prices	165000
heater repair	165000
air conditioner systems	165000
air conditioners price	165000
air conditions	165000
ac units	165000
air conditioner service	165000
service air conditioner	165000
air conditioning equipment	165000
split air conditioners	165000
car air conditioning	165000
hvac heating	165000
furnace parts	165000
ac service	135000
central air conditioning	135000
lg air conditioner	135000
central air conditioner	135000
car air conditioner	135000
service ac	135000
window unit air conditioner	135000
window air conditioning units	135000
air conditioning window units	135000
air conditioners prices	135000
repair order

auto air conditioning	135000
air conditioner reviews	135000
vent cleaning	110000
furnace repair	110000
air conditioning parts	110000
central air conditioners	110000
air conditioning services	110000
home air conditioning	110000
air conditioning home	110000
lg air conditioning	110000
split air conditioning	110000
fix air conditioning	110000
lg air conditioners	110000
fix air conditioner	110000
air condition units	110000
air conditioners reviews	110000
air conditioning servicing	110000
air conditioner servicing	110000
servicing air conditioner	110000
home air conditioner	110000
air conditioner home	110000
air duct cleaning	90500
air conditioner installation	60500
air conditioning installation	60500
air conditioning contractor	40500
hvac contractor	33100
heating contractor	33100
ac installation	27100
ac repair service	22200
air conditioner contractor	9900
ac contractor	5400
ac repair contractor	1300
ac installation service	260
ac installation contractor	–
a/c repair	–
a/c contractor	–
a/c service	–
a/c repair service	–
a/c installation contractor	–
a/c installation service	
Conventional Milling Car Service
Scraping
CONVENTIONAL MILLING car mechanical oriented services 
electrical oriented services
Bed scraping
packaging car repair
mechanice
mechanical engineering
mechanical repair
repair mechanical engineering
the branch of engineering dealing with the design, construction, and use of cars.
cars repair
repair cars
Manufacturing repairs
Manufacturing repair
Manufacturing car repair
Manufacturing car repair order
Manufacturing car maintenance
Manufacturing maintenance
car maintenance
Probuse
* INHERIT Portal My ticket: project entries (qweb)
* INHERIT Project Task form (form)
* INHERIT Sale Order (form) - add project task (form)
* INHERIT account.analytic.line.tree (tree)
* INHERIT assets_frontend_website_portal_templet (qweb)
* INHERIT hr_timesheet_sheet.sheet (form)
* INHERIT my ticket: project menu entry (qweb)
* INHERIT product.template.form.inherit (form)
* INHERIT ticket form (form)
* INHERIT website_ticket_attachment (qweb)
Display Tickets (qweb)
Car Repair Calendar (calendar)
Car Repair Request (qweb)
Car Repair Team (form)
Car Repair Team (tree)
Car Repair form (form)
Car Repair search (search)
Car Repair tree (tree)
Nature Of Service form (form)
Nature Of Service tree (tree)
Product Consume Part form (form)
Product Consume Part tree (tree)
Repair Estimation Lines form (form)
Repair Estimation Lines tree (tree)
Repair Type form (form)
Repair type tree (tree)
Success Page (qweb)
Success Ticket (qweb)
Support Invalid (qweb)
Thanks (qweb)
display ticket (qweb)
external_layout_footer_car_req (qweb)
external_layout_header_car_req (qweb)
external_layout__req (qweb)
helpesk kanban (kanban)
car.repair.support.graph (graph)
car.repair.support.pivot (pivot)
report_car_repair_req_lable (qweb)
support_report (qweb)

This module develop to handle business/industries of Car Repairs.

Main Features:
* Your Customer can send car repair request from your website and also attach documents.
* Generation of unique car request on submission and record it as car request in backend.
* Customer can check status of all car request tickets submitted by him/her on My Account page.
* Diagnosys of car repair requests and create quotation and send to your customer. * Create Job Order / Work Order and assigned to Responsible or Technician. * Configure Car Repair teams, Services, Service types. * Configure Cars and Car Parts. * Car More images. * Print PDF - Car Request
* Car Request User / Technician can communitcate with customer using chatter and fill timesheet.
* Car Request Manager can close ticket and send bill to customer (Billing from Quotation created from Diagnosys).
* Customer can give feedback and rating of Car Request.
* Manage your Car Request tickets using assignment to multiple Car Request teams.
Menus Available:
-> Repair
Repair/Configuration
Repair/Configuration/Car Repair Teams
Repair/Configuration/Service Types
Repair/Configuration/Services
Repair/Car Repairs
Repair/Car Repairs/Car Diagnosys
Repair/Car Repairs/Car Repair Tickets
Repair/Car Repairs/Car WorkOrders
Repair/Cars
Repair/Cars/Car Parts
Repair/Cars/Cars
Repair/Reports
Creating Repair Order
odoo workshop
workshop
workshop repair
repair workshop
workshop car repair



    """,
    'installable' : True,
    'application' : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
