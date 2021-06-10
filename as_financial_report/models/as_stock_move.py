# -*- coding: utf-8 -*-

from odoo import models, fields, api

class stock_move(models.Model):
    _inherit = "stock.quant"

    as_laboratorio = fields.Selection(related="product_id.product_tmpl_id.as_laboratorio",store=True)
    as_line_product = fields.Selection(related="product_id.product_tmpl_id.as_line_product",store=True)
