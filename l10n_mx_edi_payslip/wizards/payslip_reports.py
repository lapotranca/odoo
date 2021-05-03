# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from odoo import fields, models


class HrPayslipReport(models.TransientModel):
    _name = 'hr.payslip.report.detail'
    _description = 'Allow define the dates to get payslip details'

    date_from = fields.Date(
        required=True, help='The report will be generated with payslips after '
        'of this date', default=time.strftime('%Y-01-01'))
    date_to = fields.Date(
        required=True, help='The report will be generated with payslips '
        'before of this date', default=time.strftime('%Y-12-31'))
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.user.company_id)

    def print_report(self):
        return self.env.ref(
            'l10n_mx_edi_payslip.payslip_details_by_rule').report_action(self)

    def _get_lines(self):
        payslips = self.env['hr.payslip'].search([
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done'),
        ])
        categories = [cat.id for cat in self._l10n_mx_edi_get_categories()]
        return payslips.mapped('line_ids').filtered(
            lambda line: line.category_id.id in categories)

    def _l10n_mx_edi_get_details(self):
        """Return the totals by rule"""
        lines = self._get_lines()
        group = lines.read_group([
            ('id', 'in', lines.ids), ('amount', '!=', 0)], ['amount'],
            ['salary_rule_id'])
        return group

    def _l10n_mx_edi_get_details_by_category(self, rule):
        """Return the totals by category"""
        lines = self._get_lines()
        group = lines.read_group([
            ('id', 'in', lines.ids), ('amount', '!=', 0),
            ('salary_rule_id', '=', rule)], ['amount'], ['category_id'])
        return group

    def _l10n_mx_edi_get_categories(self):
        taxed = self.env.ref(
            'l10n_mx_edi_payslip.hr_salary_rule_category_perception_mx_taxed')
        exempt = self.env.ref(
            'l10n_mx_edi_payslip.hr_salary_rule_category_perception_mx_exempt')
        deduction = self.env.ref(
            'l10n_mx_edi_payslip.hr_salary_rule_category_deduction_mx')
        other = self.env.ref(
            'l10n_mx_edi_payslip.hr_salary_rule_category_other_mx')
        company = self.env.ref('hr_payroll.COMP')
        return taxed, exempt, deduction, other, company
