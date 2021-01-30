# -*- coding: utf-8 -*-

from odoo import models, fields, api

class as_purchase_order_ids(models.Model):
    _inherit = "purchase.order.line"

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    cost_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    department_id = fields.Many2one('tf.department', string='Departments')
    regiones_id = fields.Many2one('tf.regiones', string='Región')

    @api.onchange('product_id')
    def get_coste_center(self):
        usuario = self.env.user
        self.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
        self.regiones_id = usuario.regiones_purchase_id.id
        self.cost_center_id = usuario.cost_purchase_center_id.id
        self.department_id = usuario.department_puechase_id.id