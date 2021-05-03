# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def compute_sheet(self):
        """Inherit method to assign payment date in payslip created"""
        res = super(HrPayslipEmployees, self).compute_sheet()
        payslip_obj = self.env['hr.payslip']
        active_id = self.env.context.get('active_id')
        payslips = payslip_obj.search([('payslip_run_id', '=', active_id)])
        [run_data] = self.env['hr.payslip.run'].browse(active_id).read(
            ['l10n_mx_edi_payment_date']) if active_id else []
        payslips.write({
            'l10n_mx_edi_payment_date': run_data.get(
                'l10n_mx_edi_payment_date', False),
            'number': payslips[0].payslip_run_id.name if payslips else '',
        })
        return res
