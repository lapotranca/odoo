# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID, _
import odoo.addons.decimal_precision as dp
from odoo import tools
from odoo.tools.safe_eval import safe_eval
from odoo.tools import pycompat
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import float_is_zero
from datetime import datetime, date, time, timedelta
import calendar
import datetime
from dateutil.relativedelta import relativedelta
import xlsxwriter

from io import BytesIO
from pytz import timezone
import pytz
from odoo.exceptions import UserError
 

##############################################################################


from odoo.tools.misc import xlwt
import io
import base64
from xlwt  import easyxf



   

class kardex_productos_inventario(models.TransientModel):
  _name ='kardex.productos.mov'
  _description = "kardex productos"
    
  @api.model
  def get_default_date_model(self):
    return pytz.UTC.localize(datetime.now()).astimezone(timezone(self.env.user.tz or 'UTC'))

  @api.model
  def _get_from_date(self):
        company = self.env.user.company_id
        current_date = datetime.date.today()
        from_date = company.compute_fiscalyear_dates(current_date)['date_from']
        return from_date  

  excel_binary= fields.Binary('Field')
  file_name=fields.Char('Report_Name',readonly=True)
  product=fields.Many2one('product.product',string='Product',required=True)
  company=fields.Many2one('res.company',required=True,default=lambda self: self.env.user.company_id,string= 'Current Company')
  
  ubicacion=fields.Many2one('stock.location', domain=[('usage', '=', "internal")],string='Location')
  
  date_from = fields.Date(string='Date from', default=_get_from_date)
  date_to = fields.Date(string='Date to', default=fields.Date.today)
  revisio=fields.Char(string='revision')

  cantidad_inicial=fields.Float('Duantity Ini:',readonly=True)
  costo_promedio_inicial=fields.Float('Cost  Ini:',readonly=True)
  costo_total_inicial=fields.Float('Cost Total Ini:',readonly=True)

  cantidad_final=fields.Float('Quantity End :',readonly=True)
  costo_promedio=fields.Float('Cost End:',readonly=True)
  costo_total=fields.Float('Costo Total End',readonly=True)

  aplica= fields.Selection([('todas', 'All '),('ubicacion', 'By location')], required=True,default='todas',string='Selection location')

  currency_id = fields.Many2one('res.currency', string='Company currency', required=True, default=lambda self: self.env.user.company_id.currency_id,readonly=True)
  
  obj_kardex=fields.One2many(comodel_name='kardex.productos.mov.detalle',inverse_name='obj_kardex_mostrarmovi')
  
 
  
  def _action_imprimir_excel(self,):
        
    workbook = xlwt.Workbook()
    column_heading_style = easyxf('font:height 200;font:bold True;')
    worksheet = workbook.add_sheet('Kardex report')
    date_format = xlwt.XFStyle()
    date_format.num_format_str = 'dd/mm/yyyy'

    number_format = xlwt.XFStyle()
    number_format.num_format_str = '#,##0.00'
   
    #Ponemos los primeros encabezados 
    worksheet.write(0, 0, _('Kardex report product'), column_heading_style) 

    
    query_rorte = """
        select Max(id) as id  from kardex_productos_mov 
    """     
    self.env.cr.execute (query_rorte,)           
    tr = self.env.cr.dictfetchall()
    for tr_t in tr:
      todo_reporte = self.env['kardex.productos.mov'].search([('id','=',int(tr_t['id']))])  
      tf=0
      for todfact in  todo_reporte:
        worksheet.write(1, 0,"Date from:",column_heading_style)
        worksheet.write(1, 1,todfact.date_from,date_format)
        worksheet.write(2, 0,"Date to:",column_heading_style)
        worksheet.write(2, 1,todfact.date_to,date_format)
            
        worksheet.write(1, 2,"Product:",column_heading_style)    
        worksheet.write(1, 3,todfact.product.name)  
        worksheet.write(2, 2,"Current Company:",column_heading_style)    
        worksheet.write(2, 3,todfact.company.name) 
        worksheet.write(1, 4,"Location:",column_heading_style) 
        ubi_hijo=todfact.ubicacion.name
        ubi_pad=todfact.ubicacion.location_id.name
        worksheet.write(1, 5, str(ubi_pad)+"/"+str(ubi_hijo))      
  

    
    
        #Ponemos los primeros encabezados del detalle
    worksheet.write(4, 0, _('Date'), column_heading_style) 
    worksheet.write(4, 1, _('Concept'), column_heading_style)
    worksheet.write(4, 2, _('U_In'), column_heading_style)  
    worksheet.write(4, 3, _('U_Out'), column_heading_style)
    worksheet.write(4, 4, _('U_balance'), column_heading_style)
    worksheet.write(4, 5, _("Costo_Uni"), column_heading_style) 
    worksheet.write(4, 6, _('V_In'), column_heading_style)
    worksheet.write(4, 7, _('V_Out'), column_heading_style)
    worksheet.write(4, 8, _('V_balance'), column_heading_style)
    worksheet.write(4, 9, _('Costo_Prom'), column_heading_style)
    worksheet.write(4, 10, _('Origin'), column_heading_style)
    worksheet.write(4, 11, _('Pickin'), column_heading_style)
    worksheet.write(4, 12, _('Invoice'), column_heading_style)
    worksheet.write(4, 13, _('Inventory'), column_heading_style)

     
    heading="Product Kardex Detail"   
    # worksheet.write_merge(5, 0, 5,13, heading, easyxf('font:height 200; align: horiz center;pattern: pattern solid, fore_color black; font: color white; font:bold True;' "borders: top thin,bottom thin"))               
    # Se tiene que hacer de ultimo para saber cuanto mide todo
    

    # se recorre el reporte 


    todo_reporte = self.env['kardex.productos.mov.detalle'].search([('obj_kardex_mostrarmovi','=',int(tr_t['id']))])
    tf=0
    for todfact in  todo_reporte:
    
      tf+=1
      ini=5    
      worksheet.write(tf+ini,0,todfact.date,date_format) 
      worksheet.write(tf+ini,1,todfact.concepto) 
      worksheet.write(tf+ini,2,todfact.u_entrada,number_format) 
      worksheet.write(tf+ini,3,todfact.u_salida,number_format) 
      worksheet.write(tf+ini,4,todfact.u_saldo,number_format) 
      worksheet.write(tf+ini,5,todfact.costo_unit,number_format) 
      worksheet.write(tf+ini,6,todfact.v_entrada,number_format) 
      worksheet.write(tf+ini,7,todfact.v_salida,number_format) 
      worksheet.write(tf+ini,8,todfact.v_saldo,number_format) 
      worksheet.write(tf+ini,9,todfact.costo_prom,number_format) 
      worksheet.write(tf+ini,10,todfact.origin,number_format) 
      worksheet.write(tf+ini,11,todfact.picking_id.name)
      worksheet.write(tf+ini,12,todfact.account_invoice.name)
      worksheet.write(tf+ini,13,todfact.inventario.name)   



    
    fp = io.BytesIO()
    workbook.save(fp)
    excel_file = base64.encodestring(fp.getvalue())
    
    self.excel_binary = excel_file
    nombre_tabla="Kardex Report.xls"
    self.file_name=nombre_tabla
    fp.close()

 
 
  # @api.depends('company')
  # def _actualizar_compania(self):
  #   self.company=domain=[('company_id', '=', self.company.id)]
   
  @api.onchange('company')
  def _cambio_company(self):
  #       # Set ubucacion ID
   if self.company:
     return {'domain': {'ubicacion': [('company_id', '=',self.company.id),('usage', '=', "internal")]}} 


 
    



  #@api.one
  def _borracampos(self):  
   self.cantidad_inicial=""
   self.cantidad_final=""
   self.costo_promedio=""
   self.costo_total=""
   self.aplica="todas"
   self.company=""

  
  def buscar_producto(self):
    if self.date_from > self.date_to:
      raise UserError(_("The Start date cannot be less than the end date "))
    else:    
     self._borra_datos_tabla()


  def _borra_datos_tabla(self):
    query_rorte = """
        select Max(id) as id  from kardex_productos_mov 
    """     
    self.env.cr.execute (query_rorte,)           
    tr = self.env.cr.dictfetchall()
    for tr_t in tr:
     
      todo = self.env['kardex.productos.mov'].search([('id','<',int(tr_t['id']))])
      for tod in  todo: 
        tod.unlink()    

      todo_reporte = self.env['kardex.productos.mov.detalle'].search([('id','<',int(tr_t['id']))])
      for tod in  todo_reporte:

        tod.unlink()


   
    for karde in self:
      karde.obj_kardex.unlink()

    #Empezamos a realizar el saldo
    self._saldo_anterior()  

  def _saldo_anterior (self): 


    query_total=self._moviento_completo()
    query_saldo_anterior = """
      select (SUM(u_entrada)-SUM(u_salida))as u_ante , 
      (SUM(v_entrada)-SUM(v_salida))as v_ante  from (
""" + query_total+ """


)as saldo_ante where date < %s --) estes espara obteber el saldo anterior

        """
    producto=0
    producto=self.product.id       
    ubicacion=self.ubicacion.id
    date_from=self.date_from  

    if self.aplica=="todas":      
     query_saldo_anterior_param= (producto,producto,date_from)      
    
    if self.aplica=="ubicacion":
     query_saldo_anterior_param= (producto,ubicacion,producto,ubicacion,date_from)       
    
    self.env.cr.execute(query_saldo_anterior,query_saldo_anterior_param)    
      
    saldo_anterior=self.env.cr.dictfetchall()
    for linea in saldo_anterior: 
      self.cantidad_inicial=linea['u_ante']
      self.costo_total_inicial=linea['v_ante']
      if self.costo_total_inicial==0:
       self.costo_promedio_inicial=0
      if self.costo_total_inicial>0:      
       self.costo_promedio_inicial=self.costo_total_inicial/self.cantidad_inicial

    #Ponemos el saldo anteririor en la tabla
    self._saldo_anterior_tabla()


  
  def _saldo_anterior_tabla (self):  
    for kardex in self :
      concepto="Previous balance"       
      u_saldo=self.cantidad_inicial
      costo_uni=self.costo_promedio_inicial
      v_saldo=self.costo_total_inicial
      line=({'concepto':concepto,'u_saldo':u_saldo,'costo_unit':costo_uni,
             'v_saldo':v_saldo,
             })
      lines=[(0,0,line)]   
      kardex.write({'obj_kardex': lines})
    self._movimiento_producto()  
 
  def _movimiento_producto (self):
    query_total=self._moviento_completo() 
    query_movimiento="""
    select * from (
      """ + query_total +"""
      
    ) as mov where date >=%s and date <=%s 

    """   
 
    producto=0
    producto=self.product.id       
    ubicacion=self.ubicacion.id
    date_from=self.date_from
    date_to=self.date_to 

    if self.aplica=="todas":      
     query_movimiento_param= (producto,producto, date_from,date_to)            
    
    if self.aplica=="ubicacion":
     query_movimiento_param= (producto,ubicacion,producto,ubicacion, date_from,date_to)          
    
    self.env.cr.execute(query_movimiento,query_movimiento_param)  
    
    movim=self.env.cr.dictfetchall()
    for mov in movim:          
      for kardex in self :
        fecha= mov['date']   
        concepto=mov ['reference'] 
        u_entrada=mov ['u_entrada'] 
        u_salida=mov ['u_salida'] 
        u_saldo=mov ['u_saldo'] 
        costo_unit=mov ['costo_unit'] 
        v_entrada=mov ['v_entrada'] 
        v_salida=mov ['v_salida'] 
        v_saldo= mov ['v_saldo'] 
        origin=mov ['origin']
        picking_id=mov['picking_id']
        inventario=mov['inventory_id']

        
        line=({'date':fecha,'concepto':concepto,'u_entrada':u_entrada,
               'u_salida':u_salida,'u_saldo':u_saldo,'costo_unit':costo_unit,
              'v_entrada':v_entrada,'v_salida':v_salida,'v_saldo':v_saldo,
              'origin':origin,'picking_id':picking_id,'inventario':inventario,
              })
        lines=[(0,0,line)]   
        kardex.write({'obj_kardex': lines}) 
    self._saldo_final()

  def _saldo_final (self): 

    query_total=self._moviento_completo()
    query_saldo_final = """
      select (SUM(u_entrada)-SUM(u_salida))as u_saldo , 
      (SUM(v_entrada)-SUM(v_salida))as v_saldo  from (
    """ + query_total+ """

     )as saldo_ante where date <= %s --) estes espara obteber el saldo final

        """
    producto=0
    producto=self.product.id       
    ubicacion=self.ubicacion.id
    date_to=self.date_to 
    
    if self.aplica=="todas":      
     query_saldo_final_param= (producto,producto,date_to )      
    
    if self.aplica=="ubicacion":
     query_saldo_final_param= (producto,ubicacion,producto,ubicacion,date_to )      
    
    self.env.cr.execute(query_saldo_final,query_saldo_final_param)    
      
    saldo_final=self.env.cr.dictfetchall()
    for linea in saldo_final:
           
      self.cantidad_final=linea['u_saldo']      
      self.costo_total=linea['v_saldo']
      if self.costo_total >0:
       self.costo_promedio=self.costo_total/self.cantidad_final
   
    #buscamos las facturas
    self. _buscar_factura()
      
      
  
  def _moviento_completo(self):
    local_des=""
    location_id=""
    if self.aplica=="todas":
      local_des="sm.location_dest_id > 0" 
      location_id="sm.location_id > 0"
    if self.aplica=="ubicacion":
      local_des="sm.location_dest_id=%s" 
      location_id="sm.location_id=%s"    


    query_movimiento = """
 select id,CAST(date AS date),company_id, product,nombre,u_entrada,
 u_salida,u_saldo,costo_unit,v_entrada,v_salida,
v_saldo,state,origin,reference,usage,complete_name,ubicacion,inventory_id ,picking_id  
from (
-------------3)Comienza el segundo select
	select id,date_expected as date,company_id ,product_id as product,
  name as nombre,u_entrada,u_salida,
         SUM(u_entrada-u_salida)over (order by date_expected asc,id asc)as u_saldo,
         costo_unit,v_entrada,v_salida,
	SUM(v_entrada-v_salida)over (order by date_expected asc,id asc)as  v_saldo,state
  ,origin,reference,usage,
        complete_name,ubicacion,inventory_id ,picking_id  
	  from (

--------------- EMPIEZA LA UNION 

		--- unimos entradas
		select id,date_expected,product_id,name,company_id, u_entrada,u_salida,  
    costo_unit
		, v_entrada,v_salida,v_saldo,state,origin,reference,
		usage,complete_name,ubicacion,create_uid,inventory_id,picking_id   
		from 
		(
			select sm.id,sm.date_expected,sm.product_id,sm.name,sm.company_id,sm.product_qty as u_entrada,(sm.product_qty * 0)u_salida,
			(sm.price_unit) as costo_unit
			,(sm.product_qty * sm.price_unit) as v_entrada,(sm.product_qty  * 0)v_salida,(sm.product_qty  *0)v_saldo,sm.state,sm.origin,sm.reference,
			sl.usage,sl.complete_name,(sm.location_dest_id)as ubicacion,sm.create_uid,sm.inventory_id,sm.picking_id
			  from stock_move sm  inner join stock_location sl on sm.location_dest_id=sl.id where sl.usage='internal'
			 and sm.product_id=%s and sm.state='done' and """+local_des+"""

			order by date_expected asc 
		)as    sl   
							
		---- para las entrada

		UNION

		 -------------unimos salidas
		select id,date_expected,product_id,name,company_id, u_entrada,u_salida,costo_unit
		,v_entrada,v_salida,v_saldo,state,origin,reference,
		usage,complete_name,ubicacion,create_uid,inventory_id,picking_id  
		from
		   (
				select sm.id,sm.date_expected,sm.product_id,sm.name,sm.company_id,(sm.product_qty * 0) as u_entrada,
                                 sm.product_qty as u_salida,(am.amount_total_signed/sm.product_qty ) as costo_unit
                                 ,(sm.product_qty *0)as v_entrada,(am.amount_total_signed )v_salida,(sm.product_qty  *0)v_saldo,
                                  sm.state,sm.origin,sm.reference
				,sl.usage,sl.complete_name,(sm.location_id)as ubicacion,sm.create_uid,sm.inventory_id,sm.picking_id 
				  from stock_move sm  inner join stock_location sl on sm.location_id=sl.id 
           inner join account_move am on am.stock_move_id= sm.id
          where sl.usage='internal'
				   and sm.product_id=%s and sm.state='done' and """+location_id+"""
				order by date_expected asc
		  )sl 
		-------------- para las salidas

	) as kardex order by date asc -------2)TERMINA EL 2DO SELECT
)as kardex2   ------1)TERMINA EL PRIMER SELECT
        """
    return   query_movimiento  

  def _buscar_factura(self):
    for fact in self.obj_kardex:
      if fact.origin:
        query_origen = """
        select Min(id) as id from account_move where invoice_origin = %s 
        """  
        query_origen_param = (fact.origin,) 

        self.env.cr.execute (query_origen,query_origen_param) 
           
        movim = self.env.cr.dictfetchall()
        for mov in movim: 
        # #  facturas=self.env['account.invoice'].search([('origin','=',fact.origin)])
   
         fact.account_invoice = mov['id']

    self._action_imprimir_excel()    


class kardex_productos_inventario_detalle(models.TransientModel):
  _name ='kardex.productos.mov.detalle'
  _description = "kardex productos"


  obj_kardex_mostrarmovi= fields.Many2one('kardex.productos.mov')



  date=fields.Date(string='Fecha')
  concepto=fields.Char(string='Concepto')
  company_id=fields.Many2one('res.company',string= 'Compañia')
  u_entrada=fields.Float()
  u_salida=fields.Float()
  u_saldo=fields.Float()
  costo_unit=fields.Float()
  v_entrada=fields.Float()
  v_salida=fields.Float()
  v_saldo=fields.Float() 
  costo_prom=fields.Float()    
  state = fields.Char(string='Estado')
  origin=fields.Char(string='Origien') 
  picking_id=fields.Many2one('stock.picking',string='Picking')
  account_invoice=fields.Many2one('account.move',string='Factura')
  inventario=fields.Many2one('stock.inventory',string='Inventario')
  







   






        
        






    



    
       
       
        
      


    
