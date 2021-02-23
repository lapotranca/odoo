# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from babel.numbers import parse_decimal
import logging

from odoo import api, fields, models
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_mx_edi_amount_authorized_diff = fields.Float(
        'Amount Authorized Difference (Invoice)', limit=1,
        help='This field depicts the maximum difference allowed between a '
        'CFDI and an invoice. When validate an invoice will be verified that '
        'the amount total is the same of the total in the invoice, or the '
        'difference is less that this value.')
    l10n_mx_edi_employee_ids = fields.Many2many(
        'hr.employee', 'employee_journal_petty_cash', 'journal_id',
        'employee_id', help='Employees that could to use this journal.')
    is_petty_cash = fields.Boolean(
        help="Defines if this journal is to be treated as a Petty Cash")
    petty_cash_reserve = fields.Float(
        help="Amount to be allocated as permanent reserve that is to be "
        "fulfilled whenever possible")

    @api.model
    def parse_string_to_float(self, string):
        return float(parse_decimal(
            string.replace(
                (self.currency_id or self.company_id.currency_id).symbol, ''),
            locale=(self.env.context.get('lang') or
                    self.env.user.company_id.partner_id.lang or 'en_US')))

    def get_journal_dashboard_datas(self):
        res = super(AccountJournal, self).get_journal_dashboard_datas()
        currency = self.currency_id or self.company_id.currency_id
        res['is_petty_cash'] = self.is_petty_cash
        res['petty_cash_reserve_no_currency'] = self.petty_cash_reserve
        res['petty_cash_reserve'] = formatLang(
            self.env, currency.round(self.petty_cash_reserve) + 0.0,
            currency_obj=currency)
        account_balance = self.parse_string_to_float(res['account_balance'])
        to_replenish = currency.round(
            self.petty_cash_reserve - account_balance) + 0.0
        res['amount_to_replenish_no_currency'] = to_replenish
        res['amount_to_replenish'] = formatLang(
            self.env, to_replenish, currency_obj=currency)
        return res

    def create_petty_cash_replenishment(self):
        """return action to create a petty cash replenishment"""
        action = self.open_payments_action('transfer', mode='form')
        if not action.get('context'):
            return action
        if action['context'].get('default_journal_id'):
            action['context'].pop('default_journal_id')
        if action['context'].get('search_default_journal_id'):
            action['context'].pop('search_default_journal_id')
        action['context']['destination_journal_id'] = self.id
        action['context']['default_destination_journal_id'] = self.id
        res = self.get_journal_dashboard_datas()
        amount = res.get('amount_to_replenish', '0')
        action['context']['default_petty_cash_amount'] = self.parse_string_to_float(amount)  # noqa
        return action

    @api.onchange('type')
    def onchange_journal_type(self):
        if self.type != 'cash':
            self.is_petty_cash = False
            self.petty_cash_reserve = 0.0

    @api.model
    def _prepare_liquidity_account(self, name, company, currency_id, type):
        """Set account codes for the ones created for employees

        If this account is being created for an employee's journal, and there's
        a naccount set via config parameter to be used as template, assign the
        account code from it.
        """
        res = super(AccountJournal, self)._prepare_liquidity_account(
            name, company, currency_id, type)
        if not self._context.get('journal_for_employee'):
            return res

        # Check if there's an account configured to be used as template
        template_account_id = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_mx_edi_hr_expense.template_account_employee')
        if not template_account_id or not template_account_id.isdigit():
            return res

        # Check that the account actually exists
        account_model = self.env['account.account']
        template_account = account_model.browse(int(template_account_id))
        if not template_account.exists():
            return res

        # Set the code
        digits = len(template_account.code)
        prefix = template_account.code[:template_account.code.rfind('.')+1]
        code = account_model._search_new_account_code(company, digits, prefix)
        res.update({'code': code})
        return res
