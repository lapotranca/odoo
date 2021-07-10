# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError


class FinancialReportPdf(models.AbstractModel):
    """ Abstract model for generating PDF report value and send to template common for P and L and Balance Sheet"""

    _name = 'report.account_dynamic_reports.ins_report_financial'
    _description = 'Financial Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """ Provide report values to template """

        if self.env.context.get('from_js'):
            if data.get('js_data'):
                data.update({
                    'data': data.get('js_data'),
                    'report_lines': data['js_data']['report_lines'],
                    'account_report': data['js_data']['form']['account_report_id'][1],
                    'currency': data['js_data']['currency'],
                             })
            return data

        ctx = {
            'data': data,
            'report_lines': data['report_lines'],
            'account_report': data['form']['account_report_id'][1],
            'currency': data['currency'],
        }
        return ctx