# -*- coding: utf-8 -*

from odoo import models, fields

class ServiceNature(models.Model):
    _name = 'car.service.nature'
    _description = "Car Service Nature"
    
    name = fields.Char(
       string="Name",
       required=True,
    )
