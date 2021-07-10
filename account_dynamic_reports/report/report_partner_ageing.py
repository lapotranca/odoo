# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError


class InsReportPartnerAgeing(models.AbstractModel):
    _name = 'report.account_dynamic_reports.partner_ageing'

    @api.model
    def _get_report_values(self, docids, data=None):
        # If it is a call from Js window
        if self.env.context.get('from_js'):
            if data.get('js_data'):
                data.update({'Ageing_data': data.get('js_data')[1],
                             'Filters': data.get('js_data')[0],
                             'Period_Dict': data.get('js_data')[2],
                             'Period_List': data.get('js_data')[3]
                             })
        return data
