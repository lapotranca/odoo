# Copyright 2018, Vauxoo, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    accountant_company_currency_id = fields.Many2one(
        "res.users", string="Accountant MXN",
        help="This user will be the accountant assigned in the expense sheets "
        "generated for generic suppliers in MXN.")
    accountant_foreign_currency_id = fields.Many2one(
        "res.users", string="Accountant Other Currency",
        help="This user will be the accountant assigned in the expense sheets "
        "generated for generic suppliers in other currency.")
    l10n_mx_expenses_amount = fields.Float(
        'Limit amount for expenses', help='After of this amount will be '
        'notified to the employees indicated.')
    l10n_mx_edi_employee_ids = fields.Many2many(
        'hr.employee', string='Employees',
        help='When the amount in an expense is bigger than the "Limit amount '
        'for expenses" will be notified this employees.')
