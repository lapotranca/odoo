# -*- coding: utf-8 -*-

from odoo import models, fields

class Regiones(models.Model):
    _name = "tf.regiones"

    name = fields.Char('Región')
    center_ids = fields.One2many('tf.cost.center', 'regiones_id', string='Department')

class CostCenter(models.Model):
    _name = "tf.cost.center"

    name = fields.Char('Centro de Costo')
    department_ids = fields.One2many('tf.department', 'cost_center_id', string='Department')
    regiones_id = fields.Many2one('tf.regiones')

class Department(models.Model):
    _name = "tf.department"

    name = fields.Char('Departamento')
    cost_center_id = fields.Many2one('tf.cost.center')