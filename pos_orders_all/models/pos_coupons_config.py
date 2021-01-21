# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import Warning

class pos_coupons_setting(models.Model):
	_name = 'pos.coupons.setting'
	_description = "POS Gift Coupon Configuration"

	@api.constrains('min_coupan_value','max_coupan_value')
	def _check_amount(self):
		if self.min_coupan_value >= self.max_coupan_value:
			raise Warning(_("Minimum amount must be less than maximum amount"))
		if self.max_coupan_value <= self.min_coupan_value:
			raise Warning(_("Maximum amount must be greater than minimum amount")) 


	@api.model
	def create(self, vals):
		
		if self.search_count([('active','=',True)]) > 0:
			raise Warning(_('Allows only one activated Configuration of POS'))  
		else:
			return super(pos_coupons_setting,self).create(vals)

	name  = fields.Char('Name' ,default='Configuration for POS Gift Coupons')
	product_id  = fields.Many2one('product.product','Product', domain = [('type', '=', 'service'),('available_in_pos', '=', True)])
	min_coupan_value  =  fields.Float('Minimum Coupon Value')
	max_coupan_value  =  fields.Float('Maximum Coupon Value')
	max_exp_date  =  fields.Datetime('Maximum Expiry Date')
	default_name  = fields.Char('Default Name')
	default_value  =  fields.Integer('Coupon Value')
	default_availability  = fields.Integer('Total Available', default= -1)
	active  =  fields.Boolean('Active')




	
	

