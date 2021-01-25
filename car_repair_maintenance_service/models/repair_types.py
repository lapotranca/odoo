# -*- coding: utf-8 -*

from odoo import models, fields

class CarRepairtype(models.Model):
    _name = 'car.repair.type'
    _description = "Car Repair Type"
    
    name = fields.Char(
        string="Name",
        required=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
    )
    service_id = fields.Many2one(
        'car.service.nature',
        string="Service"
    )
