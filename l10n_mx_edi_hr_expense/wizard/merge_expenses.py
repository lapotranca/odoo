from odoo import models, fields, api, _
from odoo.exceptions import UserError


class L10nMxEdiMergeExpense(models.TransientModel):
    _name = 'l10n_mx_edi.merge.expense'
    _description = 'Allow to merge expenses'

    @api.model
    def default_get(self, fields_list):
        res = super(L10nMxEdiMergeExpense, self).default_get(fields_list)
        active_id = self._context.get('active_id')
        active_model = self._context.get('active_model')
        if not active_id or active_model != 'hr.expense':
            return res
        expense = self.env[active_model].browse(active_id)
        if expense.l10n_mx_edi_invoice_id:
            raise UserError(_('This expense cannot be merged, because already '
                              'has an invoice related.'))
        expenses = expense.search([
            ('partner_id', '=', expense.partner_id.id),
            ('employee_id', '=', expense.employee_id.id),
            ('l10n_mx_edi_is_to_check', '=', True),
            ('id', '!=', active_id),
        ])
        if not expenses:
            raise UserError(_(
                'No expenses were found with the same attributes that this '
                'record. (Supplier, Employee and marked to be checked)'))
        res['expense_id'] = active_id
        res['expense_ids'] = [(6, 0, expenses.ids)]
        return res

    expense_id = fields.Many2one(
        'hr.expense', 'Destination Expense',
        help='Destination expense after merge.')
    expense_ids = fields.Many2many(
        'hr.expense', string='Expenses',
        help="Expenses to merge with the current.")

    def action_merge(self):
        src = self.expense_ids
        if len(src) != 1:
            raise UserError(_('Only is possible merge with one expense.'))
        invoice = src.l10n_mx_edi_invoice_id
        self.expense_id.l10n_mx_edi_invoice_id = invoice
        self.expense_id.sheet_id = src.sheet_id
        cfdi = self.expense_id.l10n_mx_edi_get_cfdi()
        attachments = []
        for att in cfdi + self.expense_id.get_pdf_expenses():
            attachments.append(att.copy({
                'res_model': 'account.move',
                'res_id': invoice.id,
            }).id)
        invoice.l10n_mx_edi_cfdi_name = cfdi.name
        src.active = False
        src.message_post_with_view(
            'l10n_mx_edi_hr_expense.hr_expense_merge',
            values={'self': src, 'origin': self.expense_id})

    @api.onchange('expense_id')
    def onchange_expense_id(self):
        return {'domain': {'expense_ids': [
            ('partner_id', '=', self.expense_id.partner_id.id),
            ('l10n_mx_edi_is_to_check', '=', True),
            ('employee_id', '=', self.expense_id.employee_id.id)]}}
