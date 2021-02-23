# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang


class AccountMove(models.Model):
    _inherit = "account.move"

    date_invoice = fields.Date(track_visibility='onchange')
    l10n_mx_edi_expense_id = fields.Many2one(
        'hr.expense', 'Expense',
        help='Stores the expense related with this invoice')
    l10n_mx_edi_expense_sheet_id = fields.Many2one(
        'hr.expense.sheet', string='Expense Sheet',
        related='l10n_mx_edi_expense_id.sheet_id', store=True,
        help='Stores the expense sheet related with this invoice')

    def action_post(self):
        res = super().action_post()
        message = _(
            'The amount total in the CFDI is (%s) and that value is different '
            'to the invoice total (%s), that values must be consistent. '
            'Please review the invoice lines and try again. You can contact '
            'your manager to change the minimum allowed for this difference '
            'in the journal.\n\nCFDI with UUID: %s')
        label = self.env.ref(
            'l10n_mx_edi_hr_expense.tag_omit_invoice_amount_check')
        partners = self.mapped('partner_id').filtered(
            lambda par: label not in par.category_id)
        invoices = self.filtered(lambda inv: inv.l10n_mx_edi_cfdi_amount and
                                 inv.partner_id in partners)
        for invoice in invoices.filtered(lambda inv: inv.type in (
                'in_invoice', 'in_refund')):
            diff = invoice.journal_id.l10n_mx_edi_amount_authorized_diff
            if not abs(invoice.amount_total - invoice.l10n_mx_edi_cfdi_amount) > diff:  # noqa
                continue
            currency = invoice.currency_id
            raise UserError(message % (
                formatLang(self.env, invoice.l10n_mx_edi_cfdi_amount, currency_obj=currency),  # noqa
                formatLang(self.env, invoice.amount_total, currency_obj=currency),  # noqa
                invoice.l10n_mx_edi_cfdi_uuid))
        for invoice in invoices.filtered(lambda inv: inv.type in (
                'out_invoice', 'out_refund')):
            diff = invoice.journal_id.l10n_mx_edi_amount_authorized_diff
            if not abs(invoice.amount_total - invoice.l10n_mx_edi_cfdi_amount) > diff:  # noqa
                continue
            currency = invoice.currency_id
            invoice.message_post(body=message % (
                formatLang(self.env, invoice.l10n_mx_edi_cfdi_amount, currency_obj=currency),  # noqa
                formatLang(self.env, invoice.amount_total, currency_obj=currency),  # noqa
                invoice.l10n_mx_edi_cfdi_uuid))
        return res

    def action_view_expense(self):
        self.ensure_one()
        expense = self.env['hr.expense'].search([
            ('l10n_mx_edi_invoice_id', '=', self.id)], limit=1)
        if not expense:
            raise UserError(_('This invoice was not created from an expense'))
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.expense',
            'target': 'current',
            'res_id': expense.id
        }
