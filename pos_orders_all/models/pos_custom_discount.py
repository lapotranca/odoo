# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _

class PosDiscount(models.Model):
	_name = 'pos.custom.discount'
	_description = "POS Custom Discount"

	name = fields.Char('Name', required=True)
	discount = fields.Float('Discount(%)', required=True)
	description = fields.Text("Description")
	available_pos_ids = fields.Many2many('pos.session', 'pos_session_discount', 'pos_discount_id', string='Available in POS')
	
class PosSession(models.Model):
	_inherit = "pos.session"

	def _prepare_line(self, order_line):
		""" Derive from order_line the order date, income account, amount and taxes information.

		These information will be used in accumulating the amounts for sales and tax lines.
		"""
		def get_income_account(order_line):
			product = order_line.product_id
			income_account = product.with_context(force_company=order_line.company_id.id).property_account_income_id or product.categ_id.with_context(force_company=order_line.company_id.id).property_account_income_categ_id
			if not income_account:
				raise UserError(_('Please define income account for this product: "%s" (id:%d).')
								% (product.name, product.id))
			return order_line.order_id.fiscal_position_id.map_account(income_account)

		tax_ids = order_line.tax_ids_after_fiscal_position\
					.filtered(lambda t: t.company_id.id == order_line.order_id.company_id.id)
		sign = -1 if order_line.qty >= 0 else 1
		if order_line.discount_line_type == 'Percentage':
			price = sign * order_line.price_unit * (1 - (order_line.discount or 0.0) / 100.0)
		else:
			price =sign * (order_line.price_unit - order_line.discount)
		# The 'is_refund' parameter is used to compute the tax tags. Ultimately, the tags are part
		# of the key used for summing taxes. Since the POS UI doesn't support the tags, inconsistencies
		# may arise in 'Round Globally'.
		if self.company_id.tax_calculation_rounding_method == 'round_globally':
			is_refund = all(line.qty < 0 for line in order_line.order_id.lines)
		else:
			is_refund = order_line.qty < 0
		# taxes = tax_ids.compute_all(price_unit=price, quantity=abs(order_line.qty), currency=self.currency_id, is_refund=is_refund).get('taxes', [])
		tax_data = tax_ids.compute_all(price_unit=price, quantity=abs(order_line.qty), currency=self.currency_id, is_refund=is_refund)
		taxes = tax_data['taxes']
		date_order = order_line.order_id.date_order
		taxes = [{'date_order': date_order, **tax} for tax in taxes]
		return {
			'date_order': order_line.order_id.date_order,
			'income_account_id': get_income_account(order_line).id,
			'amount': order_line.price_subtotal,
			'taxes': taxes,
			'base_tags': tuple(tax_data['base_tags']),
		}   

		
class PosConfig(models.Model):
	_inherit = 'pos.config'
	
	allow_custom_discount = fields.Boolean('Allow Custom Discount')
	custom_discount_ids = fields.Many2many('pos.custom.discount', string='Discounts')
	

