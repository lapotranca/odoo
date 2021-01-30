# -*- coding: utf-8 -*-

from odoo import models, fields, api

class  as_hr_empoyee_ids(models.Model):
    _inherit = "hr.employee"

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    cost_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    departmento_id = fields.Many2one('tf.department', string='Departments')
    regiones_id = fields.Many2one('tf.regiones', string='Región')
    cost_purchase_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    department_puechase_id = fields.Many2one('tf.department', string='Departments')
    regiones_purchase_id = fields.Many2one('tf.regiones', string='Región')

    @api.onchange('regiones_id')
    def compute_centro_cost(self):
        for rec in self:
            return {'domain': {
                'cost_center_id': [('id', 'in', rec.regiones_id.center_ids.ids)]
            }}


    @api.onchange('cost_center_id')
    def compute_department(self):
        for rec in self:
            return {'domain': {
                'departmento_id': [('id', 'in', rec.cost_center_id.department_ids.ids)]
            }}

    @api.onchange('regiones_purchase_id')
    def compute_centro_cost_v(self):
        for rec in self:
            return {'domain': {
                'cost_purchase_center_id': [('id', 'in', rec.regiones_purchase_id.center_ids.ids)]
            }}


    @api.onchange('cost_purchase_center_id')
    def compute_department_v(self):
        for rec in self:
            return {'domain': {
                'department_puechase_id': [('id', 'in', rec.cost_purchase_center_id.department_ids.ids)]
            }}