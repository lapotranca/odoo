# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class POSOrderInherit(models.Model):
	_inherit = "pos.order"

	@api.depends('state','amount_total')
	def already_refunded(self):
		for refund in self:
			if refund.amount_total < 0.0:
				refund.update({
					'is_refund':True
				})

	is_refund = fields.Boolean(string='Is refund',compute='already_refunded',store=True)


class POSOrderLineInherite(models.Model):
	_inherit = "pos.order.line"


	@api.depends('profit','product_cost')
	def _compute_profitability(self):
		for line in self:
			if line.product_cost > 0.0:
				if line.product_cost >0.00:
					line['profitability'] = line.profit/line.product_cost


	@api.depends('qty','return_qty','product_id','state','deliver_qty')
	def _compute_return_rate(self):
		for line in self:
			pos_order_lines = self.env['pos.order.line'].search([('product_id','=',line.product_id.id)])
			total_qty = 0.0

			for line in pos_order_lines:
				total_qty += abs(line.deliver_qty)

			if line.return_qty > 0.0:
				rate =  (total_qty - line.return_qty)/(line.return_qty)
				line['return_rate'] = rate/100

			elif line.return_qty == 0.0 and line.qty < 0.0:
				line.update({
					'return_rate' : 0.0 
				})

	@api.depends('qty','product_id','state','return_qty')
	def _compute_deliver_qty(self):
		for line in self:
			if line.qty > 0.0:
				line['deliver_qty'] = abs(line.qty)

			if line.state != 'draft':
				if line.qty < 0.0:
					line.update({
						'deliver_qty' : line.qty
					})


	@api.depends('qty','product_id','state')
	def _compute_return_qty(self):
		for line in self:
			pos_orders = self.env['pos.order'].search([])
			for order in pos_orders:
				if (line.order_id.pos_reference == order.pos_reference) and \
					(line.order_id.partner_id.id == order.partner_id.id):
					if not (line.order_id.name == order.name):
						if line.order_id.state == 'draft' and order.state == 'paid':
							line['return_qty'] = abs(line.qty)
						elif line.order_id.state == 'paid' and order.state != 'draft':
							if line.qty < 0.0 and line.order_id.is_refund == True:
								line['return_qty'] = 0.0


	@api.depends('product_id')
	def _compute_cost_product(self):
		for line in self:
			line['product_cost'] = (line.product_id.standard_price * line.qty)

	
	@api.depends('product_cost','price_subtotal')
	def _compute_profit(self):
		for line in self:
			line['profit'] = line.price_subtotal - (line.product_cost)


	@api.depends('price_subtotal','discount', 'qty', 'price_unit', 'tax_ids', 'tax_ids_after_fiscal_position')
	def _compute_tax_amount(self):
		for line in self:
			line.update({'tax_amount' : 0.00})
			if line.tax_ids_after_fiscal_position and not line.discount:
				line.update({'tax_amount' : (line.price_subtotal_incl - (line.qty * line.price_unit))})
			if line.tax_ids_after_fiscal_position and line.discount:
				line.update({'tax_amount' : (line.price_subtotal_incl - (line.qty * line.price_unit)) +line.discount_amount})
          
             
	@api.depends('price_subtotal','discount', 'qty', 'price_unit', 'tax_ids', 'tax_ids_after_fiscal_position')           
	def _compute_tax_per(self):
		for line in self:
			line.update({'tax_per' : 0.00})
			if line.tax_ids_after_fiscal_position:
				if (line.price_unit * line.qty) > 0.0:
					line.update({'tax_per' : ((line.tax_amount  * 100)/(line.price_unit * line.qty))})



	@api.depends('price_subtotal','discount', 'qty', 'price_unit')
	def _compute_dis_amount(self):
		for line in self:
			line.update({'discount_amount' : 0.00})
			if line.discount:
				line.update({'discount_amount' : ((line.price_unit * line.discount)/100) * line.qty})


	product_cost = fields.Float(string="Cost",compute="_compute_cost_product",store=True,default=0.0)
	profit = fields.Float(string="Profit",compute="_compute_profit",store=True,default=0.0)
	order_date = fields.Datetime(string="Order Date",related="order_id.date_order",store=True)
	state = fields.Selection([('draft', 'New'), ('cancel', 'Cancelled'), ('paid', 'Paid'), ('done', 'Posted'), ('invoiced', 'Invoiced')],string="State",related="order_id.state",store=True)
	return_qty = fields.Float(string="Return Quantity",compute="_compute_return_qty",store=True,default=0.0)
	return_rate = fields.Float(string="Return Rate",compute="_compute_return_rate",store=True, default=0.000, digits='Return Rate')
	profitability = fields.Float(string="Profitability",compute="_compute_profitability",store=True,default=0.0)
	deliver_qty = fields.Float(string="Deliver Qty",compute="_compute_deliver_qty",store=True,default=0.0)
	discount_amount = fields.Float(string="Dis. Amount",compute="_compute_dis_amount",store=True)
	tax_per = fields.Float(string="Tax %", compute="_compute_tax_per",store=True)
	tax_amount = fields.Float(string="Tax amount", compute="_compute_tax_amount",store=True)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: