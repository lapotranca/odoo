# -*- coding: utf-8 -*-

from odoo import models, fields

class CostCenter(models.Model):
    _name = "tf.cost.center"

    name = fields.Char('Centro de Costo')
    department_ids = fields.One2many('tf.department', 'cost_center_id', string='Department')

class Department(models.Model):
    _name = "tf.department"

    name = fields.Char('Departamento')
    cost_center_id = fields.Many2one('tf.cost.center')