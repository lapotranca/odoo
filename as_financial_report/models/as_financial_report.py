# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

# ---------------------------------------------------------
# Account Financial Report
# ---------------------------------------------------------


class as_account_financial_report(models.Model):
    _inherit = "account.financial.report"
    _description = "Account Report"

    cost_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    department_id = fields.Many2one('tf.department', string='Departments')
    initial_balance = fields.Float('Initial Balance')