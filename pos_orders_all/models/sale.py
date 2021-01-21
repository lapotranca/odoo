# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _, tools
import psycopg2
import logging
_logger = logging.getLogger(__name__)


class PosConfiguration(models.Model):
	_inherit = 'pos.config'
	
	discount_type = fields.Selection([('percentage', "Percentage"), ('fixed', "Fixed")], string='Discount Type', default='percentage', help='Seller can apply different Discount Type in POS.')
	credit_note = fields.Selection([('create_note','Create return order Credit note'),('not_create_note','Can not Create return order Credit note')], string = "Credit note configuration" , default = "create_note")

class PosOrderInherit(models.Model):
	_inherit = 'pos.order'

	coupon_id = fields.Many2one('pos.gift.coupon')
	discount_type = fields.Char(string='Discount Type')
	return_order_ref = fields.Many2one('pos.order',string="Return Order Ref")

	def _order_fields(self, ui_order):
		res = super(PosOrderInherit, self)._order_fields(ui_order)
		if 'return_order_ref' in ui_order:
			if ui_order.get('return_order_ref') != False:
				res['return_order_ref'] = int(ui_order['return_order_ref'])
				po_line_obj = self.env['pos.order.line']
				for l in ui_order['lines']:
					line = po_line_obj.browse(int(l[2]['original_line_id']))

					if line:
						line.write({
							'return_qty' : line.return_qty - (l[2]['qty']),
						})
		return res

	def _prepare_invoice_line(self, order_line):
		res = super(PosOrderInherit, self)._prepare_invoice_line(order_line)
		res.update({
			'pos_order_line_id' : order_line.id,
			'pos_order_id' : self.id
			})
		return res

	def _prepare_invoice_vals(self):
		self.ensure_one()
		res = super(PosOrderInherit, self)._prepare_invoice_vals()
		res.update({
			'pos_order_id' : self.id
			})
		return res

	@api.model
	def _amount_line_tax(self, line, fiscal_position_id):
		taxes = line.tax_ids.filtered(lambda t: t.company_id.id == line.order_id.company_id.id)
		if fiscal_position_id:
			taxes = fiscal_position_id.map_tax(taxes, line.product_id, line.order_id.partner_id)
		if line.discount_line_type == 'Percentage':
			price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
		else:
			price = line.price_unit - line.discount
		taxes = taxes.compute_all(price, line.order_id.pricelist_id.currency_id, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)['taxes']
		return sum(tax.get('amount', 0.0) for tax in taxes)

	
	@api.model
	def _process_order(self, order, draft, existing_order):
		"""Create or update an pos.order from a given dictionary.

		:param pos_order: dictionary representing the order.
		:type pos_order: dict.
		:param draft: Indicate that the pos_order is not validated yet.
		:type draft: bool.
		:param existing_order: order to be updated or False.
		:type existing_order: pos.order.
		:returns number pos_order id
		"""
		order = order['data']
		pos_session = self.env['pos.session'].browse(order['pos_session_id'])
		if pos_session.state == 'closing_control' or pos_session.state == 'closed':
			order['pos_session_id'] = self._get_valid_session(order).id

		pos_order = False
		if not existing_order:
			pos_order = self.create(self._order_fields(order))
		else:
			pos_order = existing_order
			pos_order.lines.unlink()
			order['user_id'] = pos_order.user_id.id
			pos_order.write(self._order_fields(order))

		if pos_order.config_id.discount_type == 'percentage':
			pos_order.update({'discount_type': "Percentage"})
			pos_order.lines.update({'discount_line_type': "Percentage"})
		if pos_order.config_id.discount_type == 'fixed':
			pos_order.update({'discount_type': "Fixed"})
			pos_order.lines.update({'discount_line_type': "Fixed"})
		coupon_id = order.get('coupon_id', False)
		coup_max_amount = order.get('coup_maxamount',False)
		pos_order.write({'coupon_id':  coupon_id})
		pos_order.coupon_id.update({'coupon_count': pos_order.coupon_id.coupon_count + 1})
		pos_order.coupon_id.update({'max_amount': coup_max_amount})

		self._process_payment_lines(order, pos_order, pos_session, draft)

		if not draft:
			try:
				pos_order.action_pos_order_paid()
			except psycopg2.DatabaseError:
				# do not hide transactional errors, the order(s) won't be saved!
				raise
			except Exception as e:
				_logger.error('Could not fully process the POS Order: %s', tools.ustr(e))


		if pos_order.to_invoice and pos_order.state == 'paid':
			if pos_order.amount_total > 0:			
				pos_order.action_pos_order_invoice()
				if pos_order.discount_type and pos_order.discount_type == "Fixed":
					invoice = pos_order.account_move
					for line in invoice.invoice_line_ids : 
						pos_line = line.pos_order_line_id
						if pos_line and pos_line.discount_line_type == "Fixed":
							line.write({'price_unit':pos_line.price_unit})

			elif pos_order.amount_total < 0:
				if pos_order.session_id.config_id.credit_note == "create_note":	
					pos_order.action_pos_order_invoice()
					if pos_order.discount_type and pos_order.discount_type == "Fixed":
						invoice = pos_order.account_move
						for line in invoice.invoice_line_ids : 
							pos_line = line.pos_order_line_id
							if pos_line and pos_line.discount_line_type == "Fixed":
								line.write({'price_unit':pos_line.price_unit})

		return pos_order.id
	

class PosOrderLineInherit(models.Model):
	_inherit = 'pos.order.line'

	discount_line_type = fields.Char(string='Discount Type',readonly=True)
	original_line_id = fields.Many2one('pos.order.line', string="original Line")
	return_qty = fields.Float('Return Qty')

	def _compute_amount_line_all(self):
		self.ensure_one()
		fpos = self.order_id.fiscal_position_id
		tax_ids_after_fiscal_position = fpos.map_tax(self.tax_ids, self.product_id, self.order_id.partner_id) if fpos else self.tax_ids
		
		if self.discount_line_type == "Fixed":
			price = self.price_unit - self.discount
		else:
			price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)

		taxes = tax_ids_after_fiscal_position.compute_all(price, self.order_id.pricelist_id.currency_id, self.qty, product=self.product_id, partner=self.order_id.partner_id)
		return {
			'price_subtotal_incl': taxes['total_included'],
			'price_subtotal': taxes['total_excluded'],
		}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
