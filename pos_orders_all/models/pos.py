# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import Warning
import random
from datetime import date, datetime
from odoo.tools import float_is_zero
import pytz


class pos_create_sales_order(models.Model):
	_name = 'pos.create.sales.order'
	_description = "POS Create Sale Order"

	def create_sales_order(self, partner_id, orderlines):
		sale_object = self.env['sale.order']
		sale_order_line_obj = self.env['sale.order.line']
		order_id = sale_object.create({'partner_id': partner_id})
		for dict_line in orderlines:
			product_obj = self.env['product.product'] 
			product_dict  = dict_line.get('product')	
			product_name =product_obj.browse(product_dict .get('id')).name	
			vals = {'product_id': product_dict.get('id'),
					'name':product_name,
					'product_uom_qty': product_dict.get('quantity'),
					'price_unit':product_dict.get('price'),
					'product_uom':product_dict.get('uom_id'),
					'order_id': order_id.id}
			sale_order_line_obj.create(vals)					
		
							
		return True
		
		
class pos_order(models.Model):
	_inherit = 'pos.order'

	location_id = fields.Many2one(
		comodel_name='stock.location',
		related='config_id.stock_location_id',
		string="Location", store=True,
		readonly=True,
	)

	def create_picking(self):
		"""Create a picking for each order and validate it."""
		Picking = self.env['stock.picking']
		# If no email is set on the user, the picking creation and validation will fail be cause of
		# the 'Unable to log message, please configure the sender's email address.' error.
		# We disable the tracking in this case.
		if not self.env.user.partner_id.email:
			Picking = Picking.with_context(tracking_disable=True)
		Move = self.env['stock.move']
		StockWarehouse = self.env['stock.warehouse']
		for order in self:
			if not order.lines.filtered(lambda l: l.product_id.type in ['product', 'consu']):
				continue
			address = order.partner_id.address_get(['delivery']) or {}
			picking_type = order.picking_type_id
			return_pick_type = order.picking_type_id.return_picking_type_id or order.picking_type_id
			order_picking = Picking
			return_picking = Picking
			moves = Move
			location_id = order.location_id.id
			if order.partner_id:
				destination_id = order.partner_id.property_stock_customer.id
			else:
				if (not picking_type) or (not picking_type.default_location_dest_id):
					customerloc, supplierloc = StockWarehouse._get_partner_locations()
					destination_id = customerloc.id
				else:
					destination_id = picking_type.default_location_dest_id.id

			if picking_type:
				message = _("This transfer has been created from the point of sale session: <a href=# data-oe-model=pos.order data-oe-id=%d>%s</a>") % (order.id, order.name)
				picking_vals = {
					'origin': order.name,
					'partner_id': address.get('delivery', False),
					'user_id': False,
					'date_done': order.date_order,
					'picking_type_id': picking_type.id,
					'company_id': order.company_id.id,
					'move_type': 'direct',
					'note': order.note or "",
					'location_id': location_id,
					'location_dest_id': destination_id,
				}
				pos_qty = any([x.qty > 0 for x in order.lines if x.product_id.type in ['product', 'consu']])
				if pos_qty:
					order_picking = Picking.create(picking_vals.copy())
					if self.env.user.partner_id.email:
						order_picking.message_post(body=message)
					else:
						order_picking.sudo().message_post(body=message)
				neg_qty = any([x.qty < 0 for x in order.lines if x.product_id.type in ['product', 'consu']])
				if neg_qty:
					return_vals = picking_vals.copy()
					return_vals.update({
						'location_id': destination_id,
						'location_dest_id': return_pick_type != picking_type and return_pick_type.default_location_dest_id.id or location_id,
						'picking_type_id': return_pick_type.id
					})
					return_picking = Picking.create(return_vals)
					if self.env.user.partner_id.email:
						return_picking.message_post(body=message)
					else:
						return_picking.message_post(body=message)

			for line in order.lines.filtered(lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty, precision_rounding=l.product_id.uom_id.rounding)):
				moves |= Move.create({
					'name': line.name,
					'product_uom': line.product_id.uom_id.id,
					'picking_id': order_picking.id if line.qty >= 0 else return_picking.id,
					'picking_type_id': picking_type.id if line.qty >= 0 else return_pick_type.id,
					'product_id': line.product_id.id,
					'product_uom_qty': abs(line.qty),
					'state': 'draft',
					'location_id': location_id if line.qty >= 0 else destination_id,
					'location_dest_id': destination_id if line.qty >= 0 else return_pick_type != picking_type and return_pick_type.default_location_dest_id.id or location_id,
				})

			# prefer associating the regular order picking, not the return
			order.write({'picking_id': order_picking.id or return_picking.id})

			if return_picking:
				order._force_picking_done(return_picking)
			if order_picking:
				order._force_picking_done(order_picking)

			# when the pos.config has no picking_type_id set only the moves will be created
			if moves and not return_picking and not order_picking:
				moves._action_assign()
				moves.filtered(lambda m: m.product_id.tracking == 'none')._action_done()

		return True

	
	def return_new_order(self):
	   lines = []
	   for ln in self.lines:
		   lines.append(ln.id)
	   
	   vals = {
			'amount_total': self.amount_total,
			'date_order': self.date_order,
			'id': self.id,
			'name': self.name,
			'partner_id': [self.partner_id.id, self.partner_id.name],
			'pos_reference': self.pos_reference,
			'state': self.state,
			'session_id': [self.session_id.id, self.session_id.name],
			'company_id': [self.company_id.id, self.company_id.name],
			'lines': lines,
			'amount_tax':self.amount_tax,
			'discount_type' :self.discount_type,
			'barcode': self.barcode,
	   }
	   return vals
	
	def return_new_order_line(self):
	   
	   orderlines = self.env['pos.order.line'].search([('order_id.id','=', self.id)])
	   
	   final_lines = []
	   
	   for l in orderlines:
		   vals1 = {
				'discount': l.discount,
				'id': l.id,
				'discount_line_type':l.discount_line_type,
				'order_id': [l.order_id.id, l.order_id.name],
				'price_unit': l.price_unit,
				'product_id': [l.product_id.id, l.product_id.name],
				'qty': l.qty,
		   }
		   final_lines.append(vals1)
		   
	   return final_lines   


	def print_pos_report(self):
		return  self.env['report'].get_action(self, 'point_of_sale.report_receipt')

	def print_pos_receipt(self):
		output = []
		discount = 0
		order_id = self.search([('id', '=', self.id)], limit=1)
		barcode = order_id.barcode
		orderlines = self.env['pos.order.line'].search([('order_id', '=', order_id.id)])
		payments = self.env['pos.payment'].search([('pos_order_id', '=', order_id.id)])
		paymentlines = []
		subtotal = 0
		tax = 0
		change = 0
		for payment in payments:
			if payment.amount > 0:
				temp = {
					'amount': payment.amount,
					'name': payment.payment_method_id.name
				}
				paymentlines.append(temp)
			else:
				change += payment.amount
			 
		for orderline in orderlines:
			new_vals = {
				'product_id': orderline.product_id.display_name,
				'total_price' : orderline.price_subtotal_incl,
				'qty': orderline.qty,
				'price_unit': orderline.price_unit,
				'discount': orderline.discount,
				}

			if orderline.discount_line_type == 'percentage' :
				discount += orderline.price_unit*(orderline.discount/100)*orderline.qty

			else :
				discount += orderline.discount * orderline.qty
			
			# discount += (orderline.price_unit * orderline.qty * orderline.discount) / 100
			subtotal +=orderline.price_subtotal
			tax += (orderline.price_subtotal_incl - orderline.price_subtotal)

			subtotal +=orderline.price_subtotal
			tax += (orderline.price_subtotal_incl - orderline.price_subtotal)
			
			output.append(new_vals)
		tz = pytz.timezone(self.user_id.tz or 'UTC')
		return [output, discount, paymentlines, change, subtotal, tax,barcode, self.date_order.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")]


class pos_config(models.Model):
	_inherit = 'pos.config'

	def _get_default_location(self):
		return self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1).lot_stock_id
	
	pos_display_stock = fields.Boolean(string='Display Stock in POS')
	pos_stock_type = fields.Selection([('onhand', 'Qty on Hand'), ('incoming', 'Incoming Qty'), ('outgoing', 'Outgoing Qty'), ('available', 'Qty Available')], string='Stock Type', help='Seller can display Different stock type in POS.')
	pos_allow_order = fields.Boolean(string='Allow POS Order When Product is Out of Stock')
	pos_deny_order = fields.Char(string='Deny POS Order When Product Qty is goes down to')   
	show_stock_location = fields.Selection([
		('all', 'All Warehouse'),
		('specific', 'Current Session Warehouse'),
		], string='Show Stock Of', default='all')
	stock_location_id = fields.Many2one(
		'stock.location', string='Stock Location',
		domain=[('usage', '=', 'internal')], required=True, default=_get_default_location)

	pos_session_limit = fields.Selection([('all',  "Load all Session's Orders"), ('last3', "Load last 3 Session's Orders"), ('last5', " Load last 5 Session's Orders")], string='Session limit')
	auto_check_invoice = fields.Boolean(string='Invoice Auto Check') 
	check = fields.Boolean(string='Import Sale Order', default=False)
	allow_bag_charges = fields.Boolean('Allow Bag Charges')
	pos_bag_category_id = fields.Many2one('pos.category','Bag Charges Category')   

	
class stock_quant(models.Model):
	_inherit = 'stock.quant'


	def get_stock_location_qty(self, location):
		res = {}
		product_ids = self.env['product.product'].search([])
		for product in product_ids:
			quants = self.env['stock.quant'].search([('product_id', '=', product.id),('location_id', '=', location['id'])])
			if len(quants) > 1:
				quantity = 0.0
				for quant in quants:
					quantity += quant.quantity
				res.update({product.id : quantity})
			else:
				res.update({product.id : quants.quantity})
		return [res]

	def get_products_stock_location_qty(self, location,products):
		res = {}
		product_ids = self.env['product.product'].browse(products)
		for product in product_ids:
			quants = self.env['stock.quant'].search([('product_id', '=', product.id),('location_id', '=', location['id'])])
			if len(quants) > 1:
				quantity = 0.0
				for quant in quants:
					quantity += quant.quantity
				res.update({product.id : quantity})
			else:
				res.update({product.id : quants.quantity})
		return [res]

	def get_single_product(self,product, location):
		res = []
		pro = self.env['product.product'].browse(product)
		quants = self.env['stock.quant'].search([('product_id', '=', pro.id),('location_id', '=', location['id'])])
		if len(quants) > 1:
			quantity = 0.0
			for quant in quants:
				quantity += quant.quantity
			res.append([pro.id, quantity])
		else:
			res.append([pro.id, quants.quantity])
		return res

	
class product(models.Model):
	_inherit = 'product.product'
	
	available_quantity = fields.Float('Available Quantity')

	def get_stock_location_avail_qty(self, location):
		res = {}
		product_ids = self.env['product.product'].search([])
		for product in product_ids:
			quants = self.env['stock.quant'].search([('product_id', '=', product.id),('location_id', '=', location['id'])])
			outgoing = self.env['stock.move'].search([('product_id', '=', product.id),('location_id', '=', location['id'])])
			incoming = self.env['stock.move'].search([('product_id', '=', product.id),('location_dest_id', '=', location['id'])])
			qty=0.0
			product_qty = 0.0
			incoming_qty = 0.0
			if len(quants) > 1:
				for quant in quants:
					qty += quant.quantity

				if len(outgoing) > 0:
					for quant in outgoing:
						if quant.state not in ['done']:
							product_qty += quant.product_qty

				if len(incoming) > 0:
					for quant in incoming:
						if quant.state not in ['done']:
							incoming_qty += quant.product_qty
					product.available_quantity = qty-product_qty + incoming_qty
					res.update({product.id : qty-product_qty + incoming_qty})
			else:
				if not quants:
					if len(outgoing) > 0:
						for quant in outgoing:
							if quant.state not in ['done']:
								product_qty += quant.product_qty

					if len(incoming) > 0:
						for quant in incoming:
							if quant.state not in ['done']:
								incoming_qty += quant.product_qty
					product.available_quantity = qty-product_qty + incoming_qty
					res.update({product.id : qty-product_qty + incoming_qty})
				else:
					if len(outgoing) > 0:
						for quant in outgoing:
							if quant.state not in ['done']:
								product_qty += quant.product_qty

					if len(incoming) > 0:
						for quant in incoming:
							if quant.state not in ['done']:
								incoming_qty += quant.product_qty
					product.available_quantity = quants.quantity - product_qty + incoming_qty
					res.update({product.id : quants.quantity - product_qty + incoming_qty})
		return [res]