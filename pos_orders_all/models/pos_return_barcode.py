# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _, tools

class PosBarcode(models.Model):
	_inherit = 'pos.order'

	barcode = fields.Char(string='Barcode')
	barcode_img = fields.Binary('Order Barcode Image')

	@api.model
	def _order_fields(self, ui_order):
		res = super(PosBarcode, self)._order_fields(ui_order)
		res['barcode'] = ui_order.get('barcode')
		return res
