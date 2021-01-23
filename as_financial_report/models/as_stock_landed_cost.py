# -*- coding: utf-8 -*-

from odoo import models, fields, api

class as_stock_expense(models.Model):
    _inherit = "hr.expense"

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    cost_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    departmento_id = fields.Many2one('tf.department', string='Departments')
    regiones_id = fields.Many2one('tf.regiones', string='Región')

    @api.onchange('employee_id')
    def get_coste_center(self):
        usuario = self.env.user
        self.analytic_tag_ids = self.employee_id.analytic_tag_ids.ids
        self.regiones_id = self.employee_id.regiones_purchase_id.id
        self.cost_center_id = self.employee_id.cost_purchase_center_id.id
        self.departmento_id = self.employee_id.department_puechase_id.id

    def action_move_create(self):
        '''
        main function that is called when trying to create the accounting entries related to an expense
        '''
        move_group_by_sheet = self._get_account_move_by_sheet()

        move_line_values_by_expense = self._get_account_move_line_values()

        for expense in self:
            company_currency = expense.company_id.currency_id
            different_currency = expense.currency_id != company_currency

            # get the account move of the related sheet
            move = move_group_by_sheet[expense.sheet_id.id]

            # get move line values
            move_line_values = move_line_values_by_expense.get(expense.id)
            move_line_dst = move_line_values[-1]
            total_amount = move_line_dst['debit'] or -move_line_dst['credit']
            total_amount_currency = move_line_dst['amount_currency']

            # create one more move line, a counterline for the total on payable account
            if expense.payment_mode == 'company_account':
                if not expense.sheet_id.bank_journal_id.default_credit_account_id:
                    raise UserError(_("No credit account found for the %s journal, please configure one.") % (expense.sheet_id.bank_journal_id.name))
                journal = expense.sheet_id.bank_journal_id
                # create payment
                payment_methods = journal.outbound_payment_method_ids if total_amount < 0 else journal.inbound_payment_method_ids
                journal_currency = journal.currency_id or journal.company_id.currency_id
                payment = self.env['account.payment'].create({
                    'payment_method_id': payment_methods and payment_methods[0].id or False,
                    'payment_type': 'outbound' if total_amount < 0 else 'inbound',
                    'partner_id': expense.employee_id.address_home_id.commercial_partner_id.id,
                    'partner_type': 'supplier',
                    'journal_id': journal.id,
                    'payment_date': expense.date,
                    'state': 'reconciled',
                    'currency_id': expense.currency_id.id if different_currency else journal_currency.id,
                    'amount': abs(total_amount_currency) if different_currency else abs(total_amount),
                    'name': expense.name,
                })
                move_line_dst['payment_id'] = payment.id

            # link move lines to move, and move to expense sheet
            move.write({'line_ids': [(0, 0, line) for line in move_line_values],'as_employee_id':expense.employee_id.id})
            expense.sheet_id.write({'account_move_id': move.id})

            if expense.payment_mode == 'company_account':
                expense.sheet_id.paid_expense_sheets()

        # post the moves
        for move in move_group_by_sheet.values():
            move.post()
            for move_line in move.line_ids:
                move_line.analytic_tag_ids = self.employee_id.analytic_tag_ids.ids
                move_line.regiones_id = self.employee_id.regiones_purchase_id.id
                move_line.cost_center_id = self.employee_id.cost_purchase_center_id.id
                move_line.departmento_id = self.employee_id.department_puechase_id.id


        return move_group_by_sheet

class as_stock_expenseline(models.Model):
    _inherit = "hr.expense.sheet"

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    cost_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    departmento_id = fields.Many2one('tf.department', string='Departments')
    regiones_id = fields.Many2one('tf.regiones', string='Región')