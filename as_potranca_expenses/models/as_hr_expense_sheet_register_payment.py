# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from werkzeug import url_encode


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
                account_move_lines_to_reconcile |= line
        account_move_lines_to_reconcile.reconcile()
        move_traza = self.env['account.move'].search([('ref','=',move_payment.name)])
        for movet in move_traza:
            movet.ref = move_payment.ref


        return {'type': 'ir.actions.act_window_close'}