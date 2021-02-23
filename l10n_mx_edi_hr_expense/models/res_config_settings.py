# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    accountant_company_currency_id = fields.Many2one(
        "res.users", string="Accountant MXN", readonly=False,
        related='company_id.accountant_company_currency_id',
        help="This user will be the accountant assigned in the expense sheets "
        "generated for generic suppliers in MXN.")
    accountant_foreign_currency_id = fields.Many2one(
        "res.users", string="Accountant Other Currency", readonly=False,
        related='company_id.accountant_foreign_currency_id',
        help="This user will be the accountant assigned in the expense sheets "
        "generated for generic suppliers in other currency.")
    l10n_mx_expenses_amount = fields.Float(
        'Limit amount for expenses', readonly=False,
        related='company_id.l10n_mx_expenses_amount',
        help='After of this amount will be notified to the employees '
        'indicated.')
    l10n_mx_edi_employee_ids = fields.Many2many(
        'hr.employee', string='Employees', readonly=False,
        related='company_id.l10n_mx_edi_employee_ids',
        help='When the amount in an expense is bigger than the "Limit amount '
        'for expenses" will be notified this employees.')
