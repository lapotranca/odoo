# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_mx_edi_employee_id = fields.Many2one(
        'hr.employee', 'Employee', help='Employee that will to accrue this '
        'payment. If this payment is an advance for an supplier and must be '
        'accrue for an employee, set here it.')

    def _compute_payment_amount(self, invoices, currency, journal, date):
        """If petty cash is to be replenished then amount is to be written"""
        res = super(AccountPayment, self)._compute_payment_amount(
            invoices=invoices, currency=currency, journal=journal,
            date=date)
        if 'default_petty_cash_amount' not in self._context:
            return res
        return self._context.get('default_petty_cash_amount', 0)
