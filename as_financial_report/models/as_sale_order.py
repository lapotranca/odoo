# -*- coding: utf-8 -*-

from odoo import models, fields, api

class as_sale_order(models.Model):
    _inherit = "sale.order.line"

    # @api.onchange('regiones_id')
    # def compute_regiones(self):
    #     for rec in self:
    #         return {'domain': {
    #             'department_id': [('id', 'in', rec.regiones_id.cost_center_id.ids)]
    #         }}

    # @api.onchange('cost_center_id')
    # def compute_department(self):
    #     for rec in self:
    #         return {'domain': {
    #             'department_id': [('id', 'in', rec.cost_center_id.department_ids.ids)]
    #         }}


    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    regiones_id = fields.Many2one('tf.regiones', string='Región')
    cost_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    department_id = fields.Many2one('tf.department', string='Departments')

    @api.onchange('product_id')
    def get_coste_center(self):
        usuario = self.env.user
        self.analytic_tag_ids = usuario.analytic_tag_ids.ids
        self.regiones_id = usuario.regiones_id.id
        self.cost_center_id = usuario.cost_center_id.id
        self.department_id = usuario.departmento_id.id