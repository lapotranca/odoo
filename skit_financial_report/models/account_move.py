# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = "account.move.line"

    cost_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    department_id = fields.Many2one('tf.department', string='Departments')
    
    @api.onchange('cost_center_id')
    def compute_department(self):
        for rec in self:
            return {'domain': {
                'department_id': [('id', 'in', rec.cost_center_id.department_ids.ids)]
            }}
