# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AnalyticLine(models.Model):
    _inherit = "account.analytic.line"
    
    car_repair_request_id = fields.Many2one(
        'car.repair.support',
        string="Repair Request"
    )

#    @api.multi odoo13
#    @api.onchange('car_repair_request_id', 'car_repair_request_id.analytic_account_id') odoo13
#    def account_id_change(self):
#        for rec in self:
#            rec.account_id = rec.car_repair_request_id.analytic_account_id.id
