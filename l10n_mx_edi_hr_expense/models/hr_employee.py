# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    journal_id = fields.Many2one(
        'account.journal', 'Journal',
        domain=[('type', 'in', ['cash', 'bank'])],
        company_dependent=True,
        help='Specifies the journal that will be used to make the '
             'reimbursements to employees, for expenses with type '
             '"to reimburse"')
    journal_ids = fields.Many2many(
        'account.journal', 'employee_journal_petty_cash', 'employee_id',
        'journal_id', string='Petty Cash',
        domain=[('type', 'in', ['cash', 'bank'])],
        help='Specifies the journals that could be used to make the '
             'reimbursements to employees, for expenses with type '
             '"Petty Cash"')
    expenses_count = fields.Integer(compute='_compute_expenses')
    sheets_count = fields.Integer(compute='_compute_expenses')
    l10n_mx_edi_accountant = fields.Many2one(
        "res.users", string="Accountant",
        help="This user will be the responsible to review the expenses report "
             "after the manager actually approve it.")
    l10n_mx_edi_debit_account_id = fields.Many2one(
        'account.account', 'Debtor Number',
        related='journal_id.default_debit_account_id',
        domain=[('deprecated', '=', False)],
        help="Account defined in the journal to use when the employee receive "
        "money for expenses.")
    l10n_mx_edi_credit_account_id = fields.Many2one(
        'account.account', 'Creditor Number',
        related='journal_id.default_credit_account_id',
        domain=[('deprecated', '=', False)],
        help="Account defined in the journal to use when the employee paid "
        "an invoice from an expense.")
    l10n_mx_edi_payment_mode = fields.Selection(
        lambda self: self.env['hr.expense'].fields_get().get(
            'payment_mode').get('selection'), string='Payment Mode',
        default='own_account',
        help='Value used by default in the expenses for this employee.')

    def prepare_journal(self):
        self.ensure_one()
        journal = {
            'name': self.name,
            'code': 'E%s' % self.id,
            'type': 'cash',
        }
        return journal

    def create_petty_cash_journal(self):
        """This method is supposed to be called from the server action related
        in order to enable, disable it or post process it if needed customer
        by customer."""
        for emp in self.filtered(lambda e: not e.journal_id):
            journals = self.env['account.journal'].with_context(
                journal_for_employee=True)
            emp.journal_id = journals.create(emp.prepare_journal()).id

    def _compute_expenses(self):
        for employee in self:
            employee.update({
                'expenses_count': self.env['hr.expense'].search_count(
                    [('employee_id', '=', employee.id)]),
                'sheets_count': self.env['hr.expense.sheet'].search_count(
                    [('employee_id', '=', employee.id)]),
            })

    def action_open_sheets(self):
        self.ensure_one()
        return {
            'name': _('Expenses'),
            'view_mode': 'tree,form',
            'res_model': 'hr.expense.sheet',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('employee_id', 'in', self.ids)],
        }

    def action_open_expenses(self):
        self.ensure_one()
        return {
            'name': _('Expenses'),
            'view_mode': 'tree,form',
            'res_model': 'hr.expense',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('employee_id', 'in', self.ids)],
        }

    @api.onchange('user_id')
    def _onchange_user(self):
        if self.user_id and not self.address_home_id:
            self.address_home_id = self.user_id.partner_id
        return super(HrEmployee, self)._onchange_user()
