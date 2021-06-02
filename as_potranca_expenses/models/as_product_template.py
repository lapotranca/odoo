# -*- coding: utf-8 -*-

from odoo import models,fields,api
    
class as_product_template(models.Model):
    """Heredado modelo product.templates para agregar campos"""
    _inherit = 'product.template'
    _description = "Heredado modelo product.templates para agregar campos"

    as_expense_xml =fields.Boolean(string='Factura XML Oblogatoria') 