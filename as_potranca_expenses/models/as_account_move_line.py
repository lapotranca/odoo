# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from werkzeug import url_encode
from collections import defaultdict
from datetime import date, timedelta
from itertools import groupby
from itertools import zip_longest
from hashlib import sha256
from json import dumps
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split, email_escape_char, email_re
from odoo.tools.misc import formatLang, format_date, get_lang

class AsAccountMove(models.Model):
    _inherit = "account.move"

    as_conciliacion = fields.Boolean(string='Conciliacion agrupada')

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def as_reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        # Empty self can happen if the user tries to reconcile entries which are already reconciled.
        # The calling method might have filtered out reconciled lines.
        if not self:
            return

        # List unpaid invoices
        not_paid_invoices = self.mapped('move_id').filtered(
            lambda m: m.is_invoice(include_receipts=True) and m.invoice_payment_state not in ('paid', 'in_payment')
        )

        reconciled_lines = self.filtered(lambda aml: float_is_zero(aml.balance, precision_rounding=aml.move_id.company_id.currency_id.rounding) and aml.reconciled)
        (self - reconciled_lines)._check_reconcile_validity()
        #reconcile everything that can be
        result = self.as_auto_reconcile_lines()
        remaining_moves = result[0]

        writeoff_to_reconcile = self.env['account.move.line']
        #if writeoff_acc_id specified, then create write-off move with value the remaining amount from move in self
        if writeoff_acc_id and writeoff_journal_id and remaining_moves:
            all_aml_share_same_currency = all([x.currency_id == self[0].currency_id for x in self])
            writeoff_vals = {
                'account_id': writeoff_acc_id.id,
                'journal_id': writeoff_journal_id.id
            }
            if not all_aml_share_same_currency:
                writeoff_vals['amount_currency'] = False
            writeoff_to_reconcile = remaining_moves._create_writeoff([writeoff_vals])
            #add writeoff line to reconcile algorithm and finish the reconciliation
            remaining_moves = (remaining_moves + writeoff_to_reconcile).as_auto_reconcile_lines()[0]
        # Check if reconciliation is total or needs an exchange rate entry to be created
        (self + writeoff_to_reconcile).check_full_reconcile()

        # Trigger action for paid invoices
        not_paid_invoices.filtered(
            lambda m: m.invoice_payment_state in ('paid', 'in_payment')
        ).action_invoice_paid()

        return result[1]

    def as_auto_reconcile_lines(self):
        # Create list of debit and list of credit move ordered by date-currency
        debit_moves = self.filtered(lambda r: r.debit != 0 or r.amount_currency > 0)
        credit_moves = self.filtered(lambda r: r.credit != 0 or r.amount_currency < 0)
        debit_moves = debit_moves.sorted(key=lambda a: (a.date_maturity or a.date, a.currency_id))
        credit_moves = credit_moves.sorted(key=lambda a: (a.date_maturity or a.date, a.currency_id))
        # Compute on which field reconciliation should be based upon:
        if self[0].account_id.currency_id and self[0].account_id.currency_id != self[0].account_id.company_id.currency_id:
            field = 'amount_residual_currency'
        else:
            field = 'amount_residual'
        #if all lines share the same currency, use amount_residual_currency to avoid currency rounding error
        if self[0].currency_id and all([x.amount_currency and x.currency_id == self[0].currency_id for x in self]):
            field = 'amount_residual_currency'
        # Reconcile lines
        ret = self._as_reconcile_lines(debit_moves, credit_moves, field)
        return ret

    def _as_reconcile_lines(self, debit_moves, credit_moves, field):
        """ This function loops on the 2 recordsets given as parameter as long as it
            can find a debit and a credit to reconcile together. It returns the recordset of the
            account move lines that were not reconciled during the process.
        """
        (debit_moves + credit_moves).read([field])
        to_create = []
        cash_basis = debit_moves and debit_moves[0].account_id.internal_type in ('receivable', 'payable') or False
        cash_basis_percentage_before_rec = {}
        dc_vals ={}
        while (debit_moves and credit_moves):
            debit_move = debit_moves[0]
            credit_move = credit_moves[0]
            company_currency = debit_move.company_id.currency_id
            # We need those temporary value otherwise the computation might be wrong below
            temp_amount_residual = min(debit_move.amount_residual, -credit_move.amount_residual)
            temp_amount_residual_currency = min(debit_move.amount_residual_currency, -credit_move.amount_residual_currency)
            dc_vals[(debit_move.id, credit_move.id)] = (debit_move, credit_move, temp_amount_residual_currency)
            amount_reconcile = min(debit_move[field], -credit_move[field])

            #Remove from recordset the one(s) that will be totally reconciled
            # For optimization purpose, the creation of the partial_reconcile are done at the end,
            # therefore during the process of reconciling several move lines, there are actually no recompute performed by the orm
            # and thus the amount_residual are not recomputed, hence we have to do it manually.
            if amount_reconcile == debit_move[field]:
                debit_moves -= debit_move
            else:
                debit_moves[0].amount_residual -= temp_amount_residual
                debit_moves[0].amount_residual_currency -= temp_amount_residual_currency

            if amount_reconcile == -credit_move[field]:
                credit_moves -= credit_move
            else:
                credit_moves[0].amount_residual += temp_amount_residual
                credit_moves[0].amount_residual_currency += temp_amount_residual_currency
            #Check for the currency and amount_currency we can set
            currency = False
            amount_reconcile_currency = 0
            if field == 'amount_residual_currency':
                currency = credit_move.currency_id.id
                amount_reconcile_currency = temp_amount_residual_currency
                amount_reconcile = temp_amount_residual
            elif bool(debit_move.currency_id) != bool(credit_move.currency_id):
                # If only one of debit_move or credit_move has a secondary currency, also record the converted amount
                # in that secondary currency in the partial reconciliation. That allows the exchange difference entry
                # to be created, in case it is needed. It also allows to compute the amount residual in foreign currency.
                currency = debit_move.currency_id or credit_move.currency_id
                currency_date = debit_move.currency_id and credit_move.date or debit_move.date
                amount_reconcile_currency = company_currency._convert(amount_reconcile, currency, debit_move.company_id, currency_date)
                currency = currency.id

            if cash_basis:
                tmp_set = debit_move | credit_move
                cash_basis_percentage_before_rec.update(tmp_set._get_matched_percentage())

            to_create.append({
                'debit_move_id': debit_move.id,
                'credit_move_id': credit_move.id,
                'amount': amount_reconcile,
                'amount_currency': amount_reconcile_currency,
                'currency_id': currency,
            })

        cash_basis_subjected = []
        part_rec = self.env['account.partial.reconcile']
        for partial_rec_dict in to_create:
            debit_move, credit_move, amount_residual_currency = dc_vals[partial_rec_dict['debit_move_id'], partial_rec_dict['credit_move_id']]
            # /!\ NOTE: Exchange rate differences shouldn't create cash basis entries
            # i. e: we don't really receive/give money in a customer/provider fashion
            # Since those are not subjected to cash basis computation we process them first
            if not amount_residual_currency and debit_move.currency_id and credit_move.currency_id:
                part_rec.create(partial_rec_dict)
            else:
                cash_basis_subjected.append(partial_rec_dict)
        line_move = []
        for after_rec_dict in cash_basis_subjected:
            new_rec = part_rec.create(after_rec_dict)
            # if the pair belongs to move being reverted, do not create CABA entry
            if cash_basis and not (
                    new_rec.debit_move_id.move_id == new_rec.credit_move_id.move_id.reversed_entry_id
                    or
                    new_rec.credit_move_id.move_id == new_rec.debit_move_id.move_id.reversed_entry_id
            ):
                line_move.append(new_rec.as_create_tax_cash_basis_entry(cash_basis_percentage_before_rec))
            
        return (debit_moves+credit_moves,line_move)

class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    def as_create_tax_cash_basis_entry(self, percentage_before_rec):
        self.ensure_one()
        move_lines = []
        move_date = self.debit_move_id.date
        newly_created_move = self.env['account.move']
        cash_basis_amount_dict = defaultdict(float)
        cash_basis_base_amount_dict = defaultdict(float)
        cash_basis_amount_currency_dict = defaultdict(float)
        # We use a set here in case the reconciled lines belong to the same move (it happens with POS)
        for move in {self.debit_move_id.move_id, self.credit_move_id.move_id}:
            #move_date is the max of the 2 reconciled items
            if move_date < move.date:
                move_date = move.date
            percentage_before = percentage_before_rec[move.id]
            percentage_after = move.line_ids[0]._get_matched_percentage()[move.id]
            # update the percentage before as the move can be part of
            # multiple partial reconciliations
            percentage_before_rec[move.id] = percentage_after

            for line in move.line_ids:
                if not line.tax_exigible:
                    #amount is the current cash_basis amount minus the one before the reconciliation
                    amount = line.balance * percentage_after - line.balance * percentage_before
                    rounded_amt = self._get_amount_tax_cash_basis(amount, line)
                    if float_is_zero(rounded_amt, precision_rounding=line.company_id.currency_id.rounding):
                        continue
                    if line.tax_line_id and line.tax_line_id.tax_exigibility == 'on_payment':
                        # if not newly_created_move:
                        #     newly_created_move = self._create_tax_basis_move()
                        #create cash basis entry for the tax line
                        journal_id = self.env.user.company_id.tax_cash_basis_journal_id
                        move_lines.append({
                            'name': line.move_id.name,
                            'debit': abs(rounded_amt) if rounded_amt < 0 else 0.0,
                            'credit': rounded_amt if rounded_amt > 0 else 0.0,
                            'account_id': line.account_id.id,
                            'analytic_account_id': line.analytic_account_id.id,
                            'analytic_tag_ids': line.analytic_tag_ids.ids,
                            'tax_exigible': True,
                            'amount_currency': line.amount_currency and line.currency_id.round(-line.amount_currency * amount / line.balance) or 0.0,
                            'currency_id': line.currency_id.id,
                            # 'move_id': newly_created_move.id,
                            'partner_id': line.partner_id.id,
                            'journal_id': journal_id.id,
                            'tax_cash_basis_rec_id': self.id,
                        })
                        # Group by cash basis account and tax
                        move_lines.append({
                            'name': line.name,
                            'debit': rounded_amt if rounded_amt > 0 else 0.0,
                            'credit': abs(rounded_amt) if rounded_amt < 0 else 0.0,
                            'account_id': line.tax_repartition_line_id.account_id.id or line.account_id.id,
                            'analytic_account_id': line.analytic_account_id.id,
                            'analytic_tag_ids': line.analytic_tag_ids.ids,
                            'tax_exigible': True,
                            'amount_currency': line.amount_currency and line.currency_id.round(line.amount_currency * amount / line.balance) or 0.0,
                            'currency_id': line.currency_id.id,
                            # 'move_id': newly_created_move.id,
                            'partner_id': line.partner_id.id,
                            'journal_id': journal_id.id,
                            'tax_repartition_line_id': line.tax_repartition_line_id.id,
                            'tax_base_amount': line.tax_base_amount,
                            'tag_ids': [(6, 0, line._convert_tags_for_cash_basis(line.tag_ids).ids)],
                            'tax_cash_basis_rec_id': self.id,
                        })
                        # if line.account_id.reconcile and not line.reconciled:
                        #     #setting the account to allow reconciliation will help to fix rounding errors
                        #     to_clear_aml |= line
                        #     to_clear_aml.reconcile()
                    else:
                        #create cash basis entry for the base
                        for tax in line.tax_ids.flatten_taxes_hierarchy().filtered(lambda tax: tax.tax_exigibility == 'on_payment'):
                            # We want to group base lines as much as
                            # possible to avoid creating too many of them.
                            # This will result in a more readable report
                            # tax and less cumbersome to analyse.
                            key = self._get_tax_cash_basis_base_key(tax, move, line)
                            cash_basis_amount_dict[key] += rounded_amt
                            cash_basis_base_amount_dict[key] += line.tax_base_amount
                            cash_basis_amount_currency_dict[key] += line.currency_id.round(line.amount_currency * amount / line.balance) if line.currency_id and self.amount_currency else 0.0

        if cash_basis_amount_dict:
            # if not newly_created_move:
            #     newly_created_move = self._create_tax_basis_move()
            lines_tax = self._as_create_tax_cash_basis_base_line(cash_basis_amount_dict, cash_basis_amount_currency_dict, cash_basis_base_amount_dict,newly_created_move.journal_id)
            for taxes in lines_tax:
                move_lines.append(taxes)

        # if newly_created_move:
        #     self._set_tax_cash_basis_entry_date(move_date, newly_created_move)
        #     # post move
        #     newly_created_move.post()
        return move_lines


    def _as_get_tax_cash_basis_base_common_vals(self, key, new_move):
        self.ensure_one()
        line_id, account_id, tax_id, tax_repartition_line_id, base_tags, currency_id, partner_id, move_type = key
        # line = self.env['account.move.line'].browse(line_id)
        return {
            'name': 'tax',
            'account_id': account_id,
            'journal_id': new_move.id,
            'tax_exigible': True,
            'tax_ids': [(6, 0, [tax_id])],
            'tag_ids': [(6, 0, base_tags)],
            # 'move_id': new_move.id,
            'currency_id': currency_id,
            'partner_id': partner_id,
            'tax_repartition_line_id': tax_repartition_line_id,
        }

    def _as_create_tax_cash_basis_base_line(self, amount_dict, amount_currency_dict, tax_amount_dict, new_move):
        aml_obj = []
        for key in amount_dict.keys():
            base_line = self._as_get_tax_cash_basis_base_common_vals(key, new_move)
            currency_id = base_line.get('currency_id', False)
            rounded_amt = amount_dict[key]
            tax_base_amount = tax_amount_dict[key]
            amount_currency = amount_currency_dict[key] if currency_id else 0.0
            # aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
            aml_obj.append(dict(
                base_line,
                tax_base_amount=tax_base_amount,
                debit=rounded_amt > 0 and rounded_amt or 0.0,
                credit=rounded_amt < 0 and abs(rounded_amt) or 0.0,
                amount_currency=amount_currency))
            aml_obj.append(dict(
                base_line,
                credit=rounded_amt > 0 and rounded_amt or 0.0,
                debit=rounded_amt < 0 and abs(rounded_amt) or 0.0,
                amount_currency=-amount_currency,
                tax_repartition_line_id=False,
                tax_ids=[],
                tag_ids=[]))
        return aml_obj