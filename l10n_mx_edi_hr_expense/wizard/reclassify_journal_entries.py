from odoo import models, fields, api, _
from odoo.exceptions import UserError


class L10nMxEdiReclassifyJournalEntries(models.TransientModel):
    _name = 'l10n_mx_edi.reclassify.journal.entries'
    _description = 'Allow reclassify the journal entries'

    account_id = fields.Many2one(
        'account.account', help="An expense account is expected")
    product_id = fields.Many2one(
        'product.product', domain=[('can_be_expensed', '=', True)],
        help="Product to assign in the expenses related")
    date = fields.Date(help="Date to assign in the expenses related")

    @api.model
    def default_get(self, fields_list):
        res = super(
            L10nMxEdiReclassifyJournalEntries, self).default_get(fields_list)
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return res
        if self.env['account.move'].browse(active_ids).mapped(
                'type')[0] not in ['in_invoice', 'in_refund']:
            raise UserError(_(
                "You can only reclassify journal entries for vendor bills"))
        return res

    def reclassify_journal_entries(self):
        model = self._context.get('active_model')
        records = self._context.get('active_ids')
        if model == 'hr.expense.sheet':
            records = self.env[model].browse(records).mapped(
                'expense_line_ids').ids
        if model in ['hr.expense', 'hr.expense.sheet']:
            for exp in self.env['hr.expense'].browse(records):
                exp.account_id = self.account_id if \
                    self.account_id else exp.account_id
                exp.product_id = self.product_id if \
                    self.product_id else exp.product_id
                exp.date = self.date if self.date else exp.date
                if not exp.l10n_mx_edi_move_line_id:
                    continue
                line = exp.l10n_mx_edi_move_line_id
                state = line.move_id.state
                if state == 'posted':
                    line.move_id.button_cancel()
                line.account_id = self.account_id if \
                    self.account_id else line.account_id
                line.date = self.date if self.date else line.date
                if state == 'posted':
                    line.move_id.action_post()
        elif model == 'account.move':
            for inv in self.env['account.move'].browse(records):
                inv.date = self.date if self.date else inv.date
                for line in inv.invoice_line_ids:
                    line.account_id = self.account_id if \
                        self.account_id else line.account_id
                    line.product_id = self.product_id if \
                        self.product_id else line.product_id
                if not inv.move_id:
                    continue
                state = inv.move_id.state
                if state == 'posted':
                    inv.move_id.button_cancel()
                inv.move_id.date = self.date if self.date else inv.move_id.date
                tax_accounts = inv.tax_line_ids.mapped('account_id')
                lines = inv.move_id.line_ids.filtered(
                    lambda l: l.account_id.user_type_id.type != 'payable' and
                    l.account_id not in tax_accounts)
                for line in lines:
                    line.account_id = self.account_id if \
                        self.account_id else line.account_id
                    line.date = self.date if self.date else line.date
                if state == 'posted':
                    inv.move_id.action_post()
