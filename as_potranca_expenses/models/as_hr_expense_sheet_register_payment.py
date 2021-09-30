# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from werkzeug import url_encode
from collections import defaultdict
from itertools import groupby
from operator import itemgetter

class ASHrExpenseSheetRegisterPaymentWizard(models.TransientModel):
    _inherit = "hr.expense.sheet.register.payment.wizard"
    _description = "Expense Register Payment Wizard"

    @api.model
    def default_get(self, fields):
        result = super(ASHrExpenseSheetRegisterPaymentWizard, self).default_get(fields)
        active_id = self._context.get('active_id')
        expense_sheet = self.env['hr.expense.sheet'].browse(active_id)
        result['communication'] = expense_sheet.name
        return result

    def expense_post_payment(self):
        lines_ids = []
        self.ensure_one()
        company = self.company_id
        self = self.with_context(force_company=company.id, company_id=company.id)
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense_sheet = self.env['hr.expense.sheet'].browse(active_ids)

        # Create payment and post it
        payment = self.env['account.payment'].create(self._get_payment_vals())
        payment.post()
   

        move_payment = self.env['account.move'].search([('name','=',payment.move_name)])
        move_payment.button_draft()
        regiones_purchase_id =False
        cost_purchase_center_id =False
        department_puechase_id =False
        move_lines = []
        move_pay = []
        monto_total = 0.0
        for line in move_payment.line_ids:
            move_pay.append(line.id)
            vals = {
                'name': line.name,
                'partner_id': line.partner_id.id,
                'move_id': move_payment.id,
                'account_id': line.account_id.id,
                'debit': line.debit,
                'credit': line.credit,
                'analytic_tag_ids': line.analytic_tag_ids.ids,
                'analytic_account_id': line.analytic_account_id.id,
                'regiones_id': line.regiones_id.id,
                'cost_center_id': line.cost_center_id.id,
                'department_id': line.department_id.id,
                'payment_id': payment.id
            }
            move_lines.append((0, 0, vals))
            regiones_purchase_id =line.regiones_id.id
            cost_purchase_center_id =line.cost_center_id.id
            department_puechase_id =line.department_id.id
        move_payment.line_ids.unlink()
        move_payment.as_no_edit = True
        for line in expense_sheet.expense_line_ids:
            if line.total_amount > 0:
                vals = {
                    'name': str(line.employee_id.name)+' '+str(line.name),
                    'partner_id': line.employee_id.user_id.partner_id.id,
                    'move_id': move_payment.id,
                    'account_id': line.as_proveedor.property_account_payable_id.id,
                    'debit': line.total_amount,
                    'credit': 0,
                    'analytic_tag_ids': line.analytic_tag_ids.ids,
                    'analytic_account_id': line.analytic_account_id.id,
                    'regiones_id': line.regiones_id.id,
                    'cost_center_id': line.cost_center_id.id,
                    'department_id': line.departmento_id.id,
                }
                monto_total+=line.total_amount
                move_lines.append((0, 0, vals))
        usuario = self.env.user
        move_lines.append((0, 0, {
                'name': 'Reclasificacion de Proveedor Gasto',
                'partner_id': expense_sheet.employee_id.user_id.partner_id.id,
                'move_id': move_payment.id,
                'account_id': expense_sheet.employee_id.user_id.partner_id.property_account_payable_id.id,
                'debit': 0,
                'credit': monto_total,
                'analytic_tag_ids': line.analytic_tag_ids.ids,
                'analytic_account_id': usuario.analytic_tag_ids.ids,
                'regiones_id': regiones_purchase_id,
                'cost_center_id': cost_purchase_center_id,
                'department_id': department_puechase_id,
        }))
        move_payment.update({'line_ids':move_lines})

        move_payment.action_post()
        
        expense_sheet.state = 'done'

     # Log the payment in the chatter
        body = (_("Se ha realizado un pago %s %s con la referencia <a href='/mail/view?%s'>%s</a> relacionada con su gasto %s.") % (payment.amount, payment.currency_id.symbol, url_encode({'model': 'account.payment', 'res_id': payment.id}), payment.name, expense_sheet.name))
        expense_sheet.message_post(body=body)

        # Reconcile the payment and the expense, i.e. lookup on the payable account move lines
        account_move_lines_to_reconcile = self.env['account.move.line']
        for line in payment.move_line_ids + expense_sheet.account_move_id.line_ids:
            if line.account_id.internal_type == 'payable' and not line.reconciled:
                line.move_id.as_conciliacion = True
                account_move_lines_to_reconcile |= line
        lines = account_move_lines_to_reconcile.as_reconcile()
        self._create_tax_basis_move(lines,move_payment.ref,expense_sheet)
        move_traza = self.env['account.move'].search(['|',('ref','=',move_payment.name),('ref','=',expense_sheet.account_move_id.name)])
        for movet in move_traza:
            diario = self.env.user.company_id.tax_cash_basis_journal_id
            if movet.journal_id == diario:
                movet.ref = move_payment.ref +  diario.name


        return {'type': 'ir.actions.act_window_close'}


    def _create_tax_basis_move(self,lines,glosa,expense_sheet):
        # Check if company_journal for cash basis is set if not, raise exception
        if not self.env.user.company_id.tax_cash_basis_journal_id:
            raise UserError(_('There is no tax cash basis journal defined '
                              'for this company: "%s" \nConfigure it in Accounting/Configuration/Settings') %
                            (self.company_id.name))
        tax_cash_basis_rec_id = False
        cont = 0
        line_dict = []
        tax_group = []
        tax_extras = []
        if len(lines) > 0:
            for item in lines[0]:
                if 'tax_cash_basis_rec_id' in item:
                    tax_cash_basis_rec_id = item.pop('tax_cash_basis_rec_id')
                if 'tax_ids' in item:
                    tax_extras.append(item)
                else:
                    line_dict.append(item)
            
            lines.pop(0)
            for line in lines:
                for items in line:
                    for new_dict in line_dict:
                        if new_dict['account_id'] == items['account_id'] and new_dict['partner_id'] == items['partner_id'] and not 'tax_ids' in items:
                            if items['debit'] > 0:
                                new_dict['debit'] = new_dict['debit'] + items['debit']
                            if items['credit'] > 0:
                                new_dict['credit'] = new_dict['credit'] + items['credit']
                    if 'tax_ids' in items:
                        for new_tax in tax_extras:
                            if 'tax_ids' in new_tax:
                                if new_tax['account_id'] == items['account_id'] and new_tax['partner_id'] == items['partner_id'] and  new_tax['tax_ids'] == items['tax_ids']:
                                    if items['debit'] > 0:
                                        new_tax['debit'] = new_tax['debit'] + items['debit']
                                    if items['credit'] > 0:
                                        new_tax['credit'] = new_tax['credit'] + items['credit']
        lines_format = []
        if line_dict != []:     
            for line in line_dict:
                lines_format.append((0, 0,line))
            for tax in tax_extras:
                lines_format.append((0, 0,tax))
            move_vals = {
                'type': 'entry',
                'journal_id': self.env.user.company_id.tax_cash_basis_journal_id.id,
                'tax_cash_basis_rec_id': tax_cash_basis_rec_id,
                'ref': glosa,
                'line_ids': lines_format,
            }
            result = self.env['account.move'].create(move_vals)
            for line in result.line_ids:
                if line.name == 'tax':
                    line.name = str(expense_sheet.employee_id.name)+': '+ str(expense_sheet.name)
            result.post()
            return result
        else:
            return False