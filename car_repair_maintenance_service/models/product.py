# -*- coding: utf-8 -*

from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    car_brand = fields.Char(
        string = "Brand"
    )
    car_color = fields.Char(
        string = "Color"
    )
    car_model = fields.Char(
        string="Model"
    )
    car_year = fields.Integer(
        string="Year"
    )
    is_car = fields.Boolean(
        string="Is Car"
    )
