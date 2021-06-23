# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class as_res_user(models.Model):
    _inherit = "res.users"

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags Ventas')
    regiones_id = fields.Many2one('tf.regiones', string='Región')
    cost_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    departmento_id = fields.Many2one('tf.department', string='Departments')

    analytic_tag_purchase_ids = fields.Many2many('account.analytic.tag','as_user_id', string='Analytic Tags Compras')
    regiones_purchase_id = fields.Many2one('tf.regiones', string='Región')
    cost_purchase_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    department_puechase_id = fields.Many2one('tf.department', string='Departments')

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

class AsAnalitycTag(models.Model):
    _inherit = "account.analytic.tag"

    as_user_id = fields.Many2one('res.users', string='Usuario')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_ediat_account_posted = fields.Boolean(string="Para habilitar edicion en lineas de asiento una vez posteado", implied_group='as_financial_report.group_ediat_account_posted')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['group_ediat_account_posted'] = self.env['ir.config_parameter'].sudo().get_param('as_financial_report.group_ediat_account_posted', default=0)

        return res

    @api.model
    def set_values(self):
        self.env['ir.config_parameter'].sudo().set_param('as_financial_report.group_ediat_account_posted', self.group_ediat_account_posted)
        super(ResConfigSettings, self).set_values()

    @api.onchange('group_ediat_account_posted')
    def onchange_group_ediat_account_posted(self):
        if self.group_ediat_account_posted:
            self.module_account_accountant = True