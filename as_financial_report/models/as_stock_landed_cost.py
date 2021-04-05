# -*- coding: utf-8 -*-

from odoo import models, fields, api

class as_stock_expense(models.Model):
    _inherit = "hr.expense"

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    cost_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    departmento_id = fields.Many2one('tf.department', string='Departments')
    regiones_id = fields.Many2one('tf.regiones', string='Región')
    as_proveedor = fields.Many2one('res.partner', string='Proveedor')
    as_vat = fields.Char(string='RFC',related="as_proveedor.vat")

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

    def _get_account_move_line_values(self):
        move_line_values_by_expense = {}
        for expense in self:
            move_line_name = expense.employee_id.name + ': ' + expense.name.split('\n')[0][:64]
            account_src = expense._get_expense_account_source()
            account_dst = expense._get_expense_account_destination()
            account_date = expense.sheet_id.accounting_date or expense.date or fields.Date.context_today(expense)

            company_currency = expense.company_id.currency_id
            different_currency = expense.currency_id and expense.currency_id != company_currency

            move_line_values = []
            taxes = expense.tax_ids.with_context(round=True).compute_all(expense.unit_amount, expense.currency_id, expense.quantity, expense.product_id)
            total_amount = 0.0
            total_amount_currency = 0.0
            partner_id = expense.as_proveedor.id
            

            # source move line
            amount = taxes['total_excluded']
            amount_currency = False
            if different_currency:
                amount = expense.currency_id._convert(amount, company_currency, expense.company_id, account_date)
                amount_currency = taxes['total_excluded']
            move_line_src = {
                'name': move_line_name,
                'quantity': expense.quantity or 1,
                'debit': amount if amount > 0 else 0,
                'credit': -amount if amount < 0 else 0,
                'amount_currency': amount_currency if different_currency else 0.0,
                'account_id': account_src.id,
                'product_id': expense.product_id.id,
                'product_uom_id': expense.product_uom_id.id,
                'analytic_account_id': expense.analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, expense.analytic_tag_ids.ids)],
                'expense_id': expense.id,
                'partner_id': partner_id,
                'tax_ids': [(6, 0, expense.tax_ids.ids)],
                'tag_ids': [(6, 0, taxes['base_tags'])],
                'currency_id': expense.currency_id.id if different_currency else False,
            }
            move_line_values.append(move_line_src)
            total_amount += -move_line_src['debit'] or move_line_src['credit']
            total_amount_currency += -move_line_src['amount_currency'] if move_line_src['currency_id'] else (-move_line_src['debit'] or move_line_src['credit'])

            # taxes move lines
            for tax in taxes['taxes']:
                amount = tax['amount']
                amount_currency = False
                if different_currency:
                    amount = expense.currency_id._convert(amount, company_currency, expense.company_id, account_date)
                    amount_currency = tax['amount']

                if tax['tax_repartition_line_id']:
                    rep_ln = self.env['account.tax.repartition.line'].browse(tax['tax_repartition_line_id'])
                    base_amount = self.env['account.move']._get_base_amount_to_display(tax['base'], rep_ln)
                else:
                    base_amount = None

                move_line_tax_values = {
                    'name': tax['name'],
                    'quantity': 1,
                    'debit': amount if amount > 0 else 0,
                    'credit': -amount if amount < 0 else 0,
                    'amount_currency': amount_currency if different_currency else 0.0,
                    'account_id': tax['account_id'] or move_line_src['account_id'],
                    'tax_repartition_line_id': tax['tax_repartition_line_id'],
                    'tag_ids': tax['tag_ids'],
                    'tax_base_amount': base_amount,
                    'expense_id': expense.id,
                    'partner_id': partner_id,
                    'currency_id': expense.currency_id.id if different_currency else False,
                    'analytic_account_id': expense.analytic_account_id.id if tax['analytic'] else False,
                    'analytic_tag_ids': [(6, 0, expense.analytic_tag_ids.ids)] if tax['analytic'] else False,
                }
                total_amount -= amount
                total_amount_currency -= move_line_tax_values['amount_currency'] or amount
                move_line_values.append(move_line_tax_values)

            # destination move line
            move_line_dst = {
                'name': move_line_name,
                'debit': total_amount > 0 and total_amount,
                'credit': total_amount < 0 and -total_amount,
                'account_id': account_dst,
                'date_maturity': account_date,
                'amount_currency': total_amount_currency if different_currency else 0.0,
                'currency_id': expense.currency_id.id if different_currency else False,
                'expense_id': expense.id,
                'partner_id': partner_id,
            }
            move_line_values.append(move_line_dst)

            move_line_values_by_expense[expense.id] = move_line_values
        return move_line_values_by_expense

class as_stock_expenseline(models.Model):
    _inherit = "hr.expense.sheet"

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    cost_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    departmento_id = fields.Many2one('tf.department', string='Departments')
    regiones_id = fields.Many2one('tf.regiones', string='Región')